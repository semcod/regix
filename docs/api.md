# Regix — API Reference

## Top-level imports

```python
from regix import (
    Regix,
    Snapshot,
    RegressionReport,
    Regression,
    Improvement,
    RegressionConfig,
    SymbolMetrics,
    MetricDelta,
)
```

---

## `RegressionConfig`

```python
@dataclass
class RegressionConfig:
    cc_max: float = 15.0
    mi_min: float = 20.0
    coverage_min: float = 80.0
    length_max: int = 100
    docstring_min: float = 60.0
    delta_warn: float = 2.0
    delta_error: float = 5.0
    exclude: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    backends: dict[str, str] = field(default_factory=dict)
    on_regression: str = "warn"       # "warn" | "error" | "block"
    show_improvements: bool = True
    workdir: str | Path = "."
```

### `RegressionConfig.from_file(path)`

```python
@classmethod
def from_file(cls, path: str | Path) -> RegressionConfig
```

Load configuration from a YAML file. Searches for `regix.yaml`, `.regix/config.yaml`, or `pyproject.toml` `[tool.regix]` section if `path` is a directory.

**Raises** `FileNotFoundError` if no config file is found and `path` is a directory.

### `RegressionConfig.from_dict(data)`

```python
@classmethod
def from_dict(cls, data: dict) -> RegressionConfig
```

---

## `SymbolMetrics`

Holds all tracked metrics for a single symbol (function, class, or module).

```python
@dataclass
class SymbolMetrics:
    file: str              # relative path from workdir
    symbol: str | None     # function/class name; None = module-level aggregate
    line_start: int | None
    line_end: int | None
    cc: float | None           # cyclomatic complexity
    mi: float | None           # maintainability index (0–100)
    length: int | None         # function body length in lines
    coverage: float | None     # line coverage (0–100)
    docstring_coverage: float | None
    quality_score: float | None  # vallm score (0–1)
    imports: int | None        # number of import statements (module-level)
    raw: dict                  # backend-specific raw values
```

---

## `Snapshot`

An immutable, content-addressed record of all `SymbolMetrics` for a codebase at a point in time.

```python
@dataclass(frozen=True)
class Snapshot:
    ref: str                         # git ref or "local"
    commit_sha: str | None           # resolved SHA, None for "local"
    timestamp: datetime
    workdir: Path
    symbols: tuple[SymbolMetrics, ...]
    backend_versions: dict[str, str] # {"lizard": "1.17", ...}
```

### `Snapshot.from_ref(ref, workdir, config, backends)`

```python
@classmethod
def from_ref(
    cls,
    ref: str,
    workdir: str | Path = ".",
    config: RegressionConfig | None = None,
    backends: list[str] | None = None,
    use_cache: bool = True,
) -> Snapshot
```

Capture metrics at a git ref. If `ref == "local"`, analyses the current working tree without any git operations. Otherwise, uses `git stash` + `git checkout` + analysis + `git checkout -` to restore the working tree safely.

**Parameters:**
- `ref` — Any valid git ref: `"HEAD"`, `"HEAD~3"`, `"main"`, `"v1.2.0"`, `"abc1234"`, or `"local"`.
- `backends` — Which analysis backends to run. Defaults to all configured backends.
- `use_cache` — If `True`, returns a cached snapshot if the commit SHA and backend versions match.

**Raises:**
- `GitRefError` — if `ref` cannot be resolved.
- `GitDirtyError` — if working tree is dirty and `ref != "local"` and stashing fails.
- `BackendError` — if a required backend is not installed.

### `Snapshot.load(path)`

```python
@classmethod
def load(cls, path: str | Path) -> Snapshot
```

Deserialise a previously saved snapshot from a JSON file.

### `Snapshot.save(path)`

```python
def save(self, path: str | Path) -> None
```

### `Snapshot.get(file, symbol)`

```python
def get(self, file: str, symbol: str | None = None) -> SymbolMetrics | None
```

Look up metrics for a specific file and optional symbol.

### `Snapshot.metrics`

```python
@property
def metrics(self) -> dict[str, dict[str, SymbolMetrics]]
```

Nested dict: `metrics[file][symbol] → SymbolMetrics`. Use `symbol=None` for module-level entries.

---

## `MetricDelta`

```python
@dataclass
class MetricDelta:
    metric: str
    before: float | None
    after: float | None
    delta: float | None     # after - before; None if either side is None
    is_regression: bool
    is_improvement: bool
    severity: str           # "error" | "warning" | "info" | "ok"
    threshold: float | None
```

---

## `Regression`

```python
@dataclass
class Regression:
    file: str
    symbol: str | None
    line: int | None          # line in the *after* snapshot
    metric: str
    before: float
    after: float
    delta: float
    severity: str             # "error" | "warning"
    threshold: float
    ref_before: str
    ref_after: str
```

---

## `Improvement`

```python
@dataclass
class Improvement:
    file: str
    symbol: str | None
    line: int | None
    metric: str
    before: float
    after: float
    delta: float              # negative = improved (for cc, length, imports)
    ref_before: str
    ref_after: str
```

---

## `RegressionReport`

Aggregated result of a comparison between two snapshots.

```python
@dataclass
class RegressionReport:
    ref_before: str
    ref_after: str
    snapshot_before: Snapshot
    snapshot_after: Snapshot
    regressions: list[Regression]
    improvements: list[Improvement]
    unchanged: int              # symbol count with no metric change
    errors: int                 # count of Regression with severity="error"
    warnings: int               # count of Regression with severity="warning"
    stagnated: bool             # True if identical to a previously seen report
    duration: float             # seconds to produce the report
```

### Properties

```python
@property
def has_errors(self) -> bool:
    return self.errors > 0

@property
def has_regressions(self) -> bool:
    return len(self.regressions) > 0

@property
def passed(self) -> bool:
    return self.errors == 0

@property
def summary(self) -> str:
    """One-line human-readable summary."""
```

### `RegressionReport.to_dict()`

```python
def to_dict(self) -> dict
```

Serialise to a plain dict suitable for `json.dumps`.

### `RegressionReport.to_json(indent)`

```python
def to_json(self, indent: int = 2) -> str
```

### `RegressionReport.to_yaml()`

```python
def to_yaml(self) -> str
```

### `RegressionReport.to_toon()`

```python
def to_toon(self) -> str
```

TOON format (machine-readable plain text, compatible with vallm/pyqual toon files):

```
# regix compare | HEAD~1 → HEAD | 2e 3w 5i | 2026-03-31

SUMMARY:
  compared: 127 symbols  errors: 2  warnings: 3  improvements: 5

ERRORS[2]{file,symbol,metric,before,after,delta}:
  pyqual/cli.py,_build_run_summary,cc,12,18,+6
  pyqual/validation.py,validate_config,cc,18,26,+8

WARNINGS[3]{file,symbol,metric,before,after,delta}:
  pyqual/cli.py,bulk_run_cmd,cc,14,19,+5
  pyqual/cli.py,run,mi,45,38,-7
  pyqual/validation.py,validate_config,length,92,110,+18

IMPROVEMENTS[5]{file,symbol,metric,before,after,delta}:
  pyqual/bulk_init.py,_collect_pyproject_metadata,cc,9,6,-3
  ...
```

### `RegressionReport.filter(file, symbol, metric, severity)`

```python
def filter(
    self,
    file: str | None = None,
    symbol: str | None = None,
    metric: str | None = None,
    severity: str | None = None,
) -> RegressionReport
```

Return a new report containing only entries matching the given filters. All filters are `None`-means-any.

---

## `Regix`

The main entry point. Wraps `Snapshot`, `compare`, and `history` with a unified interface.

```python
class Regix:
    def __init__(
        self,
        config: RegressionConfig | str | Path | None = None,
        workdir: str | Path = ".",
    )
```

If `config` is a `str` or `Path`, it is passed to `RegressionConfig.from_file`. If `None`, Regix searches for a config file starting from `workdir`.

### `Regix.snapshot(ref, use_cache)`

```python
def snapshot(
    self,
    ref: str = "HEAD",
    use_cache: bool = True,
) -> Snapshot
```

### `Regix.compare(ref_before, ref_after, use_cache)`

```python
def compare(
    self,
    ref_before: str = "HEAD~1",
    ref_after: str = "HEAD",
    use_cache: bool = True,
) -> RegressionReport
```

Capture snapshots for both refs (from cache if available) and run the comparison engine.

### `Regix.compare_local(ref_before)`

```python
def compare_local(
    self,
    ref_before: str = "HEAD",
) -> RegressionReport
```

Compare a git ref against the current (possibly dirty) working tree. Does not stash or modify the working tree.

### `Regix.history(depth, ref, metrics)`

```python
def history(
    self,
    depth: int = 20,
    ref: str = "HEAD",
    metrics: list[str] | None = None,
) -> HistoryReport
```

Walk `depth` commits starting from `ref` and return a `HistoryReport` with a metric timeline.

### `Regix.check_gates(ref)`

```python
def check_gates(self, ref: str = "HEAD") -> GateResult
```

Check the current state (or any ref) against the configured thresholds **without** comparison. Equivalent to running a linter, not a regression check.

---

## `HistoryReport`

```python
@dataclass
class HistoryReport:
    commits: list[CommitMetrics]     # ordered newest → oldest
    regressions: list[HistoryRegression]
    trends: dict[str, TrendLine]     # metric → TrendLine
```

### `CommitMetrics`

```python
@dataclass
class CommitMetrics:
    sha: str
    ref: str | None
    timestamp: datetime
    author: str
    message: str          # first line only
    metrics: dict[str, float]  # aggregated: {"cc_avg", "cc_max", "coverage", ...}
```

### `HistoryRegression`

```python
@dataclass
class HistoryRegression:
    sha_start: str        # commit where regression first appeared
    sha_end: str          # most recent commit where it persists
    file: str
    symbol: str | None
    metric: str
    value_before: float   # value at parent of sha_start
    value_worst: float    # worst observed value in the range
    value_current: float  # current value at sha_end
    commits_affected: int
```

### `TrendLine`

```python
@dataclass
class TrendLine:
    metric: str
    values: list[float]       # one per commit, newest first
    slope: float              # linear regression slope (positive = worsening trend)
    is_degrading: bool        # True if slope > configured trend_warn_slope
```

---

## Backends

Each backend implements:

```python
class BackendBase(ABC):
    name: str
    required_binary: str | None

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
    ) -> list[SymbolMetrics]: ...

    def version(self) -> str: ...
```

### Built-in backends

| Backend | `name` | Provides | Requires |
|---------|--------|----------|----------|
| `LizardBackend` | `"lizard"` | `cc`, `length` | `lizard` |
| `RadonBackend` | `"radon"` | `mi`, raw metrics | `radon` |
| `CoverageBackend` | `"coverage"` | `coverage` | `pytest-cov`, `.coverage` file |
| `VallmBackend` | `"vallm"` | `quality_score` | `vallm` |
| `DocstringBackend` | `"docstring"` | `docstring_coverage` | built-in (`ast`) |

### Registering a custom backend

```python
from regix.backends import register_backend, BackendBase
from regix import SymbolMetrics, RegressionConfig
from pathlib import Path

class MyBackend(BackendBase):
    name = "mybackend"
    required_binary = "mytool"

    def is_available(self) -> bool:
        import shutil
        return shutil.which("mytool") is not None

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
    ) -> list[SymbolMetrics]:
        results = []
        for f in files:
            # run mytool, parse output, build SymbolMetrics
            results.append(SymbolMetrics(
                file=str(f.relative_to(workdir)),
                symbol=None,
                line_start=None, line_end=None,
                cc=None, mi=None, length=None,
                coverage=None, docstring_coverage=None,
                quality_score=None, imports=None,
                raw={"mytool_score": 0.95},
            ))
        return results

register_backend(MyBackend())
```

---

## Git helpers (`regix.git`)

These are public utilities for working with git refs and worktrees. They are used internally but exposed for use in scripts and custom integrations.

```python
from regix.git import (
    resolve_ref,
    list_commits,
    checkout_temporary,
    get_dirty_files,
    is_clean,
)
```

### `resolve_ref(ref, workdir)`

```python
def resolve_ref(ref: str, workdir: Path = Path(".")) -> str
```

Resolve a symbolic ref to a commit SHA. Returns the SHA string.

**Raises** `GitRefError` if the ref cannot be resolved.

### `list_commits(ref, depth, workdir)`

```python
def list_commits(
    ref: str = "HEAD",
    depth: int = 20,
    workdir: Path = Path("."),
) -> list[CommitInfo]
```

Returns a list of `CommitInfo(sha, timestamp, author, message)` starting from `ref`, newest first.

### `checkout_temporary(ref, workdir)`

```python
@contextmanager
def checkout_temporary(
    ref: str,
    workdir: Path = Path("."),
) -> Iterator[Path]
```

Context manager. Stashes any local changes, checks out `ref` into a temporary directory (using `git worktree add`), yields the worktree path, then cleans up and pops the stash. The original working tree is never modified.

```python
from regix.git import checkout_temporary

with checkout_temporary("HEAD~3", workdir=Path(".")) as tmp:
    # tmp is a Path to a clean worktree at HEAD~3
    metrics = collect_metrics(tmp)
# back to original state
```

### `is_clean(workdir)`

```python
def is_clean(workdir: Path = Path(".")) -> bool
```

Returns `True` if there are no uncommitted changes.

### `get_dirty_files(workdir)`

```python
def get_dirty_files(workdir: Path = Path(".")) -> list[Path]
```

Returns a list of files with uncommitted changes (modified + untracked).

---

## Exceptions

```python
class RegixError(Exception): ...

class GitRefError(RegixError):
    """Raised when a git ref cannot be resolved."""
    ref: str

class GitDirtyError(RegixError):
    """Raised when the working tree is dirty and the operation requires a clean state."""
    dirty_files: list[str]

class BackendError(RegixError):
    """Raised when a backend fails to produce output."""
    backend: str
    cause: Exception | None

class ConfigError(RegixError):
    """Raised when the configuration file is invalid."""
    path: str | None
    detail: str
```

---

## Gate result (`regix.gates`)

```python
from regix.gates import GateResult, GateCheck

@dataclass
class GateCheck:
    metric: str
    value: float
    threshold: float
    operator: str     # "le" | "ge" | "eq"
    passed: bool
    source: str       # "snapshot" | "comparison"

@dataclass
class GateResult:
    checks: list[GateCheck]
    all_passed: bool
    errors: list[GateCheck]
    warnings: list[GateCheck]
```

---

## pyqual integration (`regix.integrations.pyqual`)

```python
from regix.integrations.pyqual import (
    RegixCollector,       # GateSet-compatible metric collector
    REGIX_PRESET,         # ToolPreset for use in pyqual tools registry
)
```

### `RegixCollector`

A drop-in metric collector for pyqual's `GateSet`. Reads `.regix/report.toon.yaml` and returns `{"regression_errors": N, "regression_warnings": N}`.

```python
from regix.integrations.pyqual import RegixCollector
from pyqual.gates import GateSet
from pyqual.config import GateConfig

gate_set = GateSet(
    gates=[
        GateConfig(metric="regression_errors", operator="eq", threshold=0),
        GateConfig(metric="regression_warnings", operator="le", threshold=5),
    ],
    extra_collectors=[RegixCollector()],
)
results = gate_set.check_all(Path("."))
```

### `REGIX_PRESET`

```python
REGIX_PRESET = ToolPreset(
    binary="regix",
    command="regix compare HEAD~1 HEAD --format toon --output .regix/",
    allow_failure=False,
)
```

Register it in a custom pyqual tools module or reference `tool: regix` in `pyqual.yaml` after installing the `regix[pyqual]` extra.
