# Regix — Regression Index for Python Code Quality


## AI Cost Tracking

![AI Cost](https://img.shields.io/badge/AI%20Cost-$3.15-green) ![AI Model](https://img.shields.io/badge/AI%20Model-openrouter%2Fqwen%2Fqwen3-coder-next-lightgrey)

This project uses AI-generated code. Total cost: **$3.1500** with **21** AI commits.

Generated on 2026-04-07 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/models/openrouter/qwen/qwen3-coder-next)

---

**Regix** is a Python library for detecting, measuring, and reporting code quality regressions between versions of a codebase. It compares static analysis metrics across git commits, branches, or local snapshots and pinpoints exactly which functions, classes, or lines have regressed — and by how much.

> Inspired by operational experience with [pyqual](https://github.com/semcod/pyqual): iterative quality-gate pipelines revealed that without structured regression tracking, metric changes across refactoring cycles are invisible until a gate breaks.

> **Why "Regix"?** From **reg**ression + **ix** (like fix/matrix vibe). Short, technical, memorable.

---

## Problem statement

When refactoring code over multiple iterations:

- A function's cyclomatic complexity improves in one commit, then regresses two commits later.
- Test coverage drops by 3 % after a merge — but no single file is obviously responsible.
- Maintainability index worsens across three files simultaneously; the cause is spread over dozens of small changes.
- A CI pipeline fails a quality gate without explaining *what changed* since the last passing run.

Standard linters and quality tools report the **current state**. They do not answer: *"Is this better or worse than before, and where exactly did it change?"*

**Regix answers that question.**

---

## What Regix does

```
git commit A  ──►  snapshot_A  ─┐
                                ├──► compare ──► regression report
git commit B  ──►  snapshot_B  ─┘
```

For every function, class, and module it tracks:

| Metric | Unit | Regression when |
|---|---|---|
| Cyclomatic complexity (CC) | integer | increases |
| Maintainability index (MI) | 0–100 | decreases |
| Test coverage | % | decreases |
| Function length | lines | increases beyond threshold |
| Docstring coverage | % | decreases |
| LLM validation score | 0–1 | decreases (via vallm) |
| Import count | integer | increases |
| Fan-out (delegation depth) | integer | decreases (shell/stub regression) |
| Call count | integer | decreases (hollowing out) |
| Symbol count | integer | decreases (monolith collapse) |
| Parameter count | integer | increases (interface bloat) |
| Node type diversity | integer | decreases (structural uniformity) |
| Logic density | ratio | decreases (empty body regression) |

In addition to per-metric regressions, Regix detects **architectural smells** — cross-symbol patterns that indicate structural degradation even when individual metrics look acceptable:

| Smell | Pattern |
|---|---|
| `god_function` | One function absorbed CC from several that were deleted |
| `stub_regression` | `fan_out` and `call_count` drop to near-zero (mock/stub replacing real logic) |
| `monolith_collapse` | `symbol_count` drops while total file length grows |
| `shell_cluster` | Multiple functions simultaneously lose delegation depth |
| `logic_drain` | `logic_density` drops across ≥ 3 functions in a file |

Regressions are reported at **three granularity levels**:

1. **Line** — the exact line range that changed and caused the metric shift.
2. **Symbol** — the function or class whose metric crossed a threshold.
3. **Module** — the file-level aggregate delta.

---

## Key features

- **Git-native**: compares any two refs (`HEAD~1`, branch names, tags, commit SHAs).
- **Local-snapshot mode**: compare a dirty working tree against any historical ref without committing.
- **Multi-version history**: compute a regression timeline across N commits to see trends.
- **Configurable thresholds**: per-metric, per-file, or per-symbol severity rules.
- **Multiple backends**: lizard (CC), radon (MI), pytest-cov (coverage), vallm (LLM quality), structure (AST fan-out/call analysis), architecture (cross-symbol smell detection).
- **Machine-readable output**: JSON, YAML, or TOON format for CI integration.
- **Human-readable output**: rich terminal tables and diff-style reports.
- **Zero false-positives mode**: only report regressions that cross a configured threshold delta.

---

## Installation

```bash
pip install regix
```

With optional analysis backends:

```bash
pip install "regix[full]"      # lizard + radon + vallm + pytest-cov
pip install "regix[lizard]"    # CC + length analysis only
pip install "regix[coverage]"  # pytest-cov integration only
pip install "regix[vallm]"     # LLM-based quality scoring
```

Python requirement: **>= 3.9**

---

## Quick start

### Compare HEAD against previous commit

```bash
regix compare HEAD~1 HEAD
```

```
Regression Report: HEAD~1 → HEAD
════════════════════════════════════════════════════════════
  pyqual/cli.py
    ▲ bulk_run_cmd        CC  14 → 19  (+5)   ⚠ WARNING
    ▲ _build_run_summary  CC  12 → 18  (+6)   ✗ ERROR
    ▼ run                 MI  45 → 38  (-7)   ⚠ WARNING

  pyqual/validation.py
    ▲ validate_config     CC  18 → 26  (+8)   ✗ ERROR
    ▲ validate_config     len 92 → 110 (+18)  ⚠ WARNING

Summary: 2 errors, 3 warnings, 0 improvements across 2 files
Gates: ✗ FAIL  (cc_max=15 violated in 4 symbols)
```

### Compare two branches

```bash
regix compare main feature/refactor --format json > regression.json
```

### Track regression over last 10 commits

```bash
regix history --depth 10 --metric cc --metric coverage
```

```
Commit    cc_avg  cc_max  coverage  mi_avg
────────  ──────  ──────  ────────  ──────
abc1234   6.2     19      59.9 %    38.4     ← current HEAD
def5678   6.0     18      61.2 %    39.1
ghi9012   5.8     16      63.0 %    41.2     ← coverage regression starts here
jkl3456   5.7     15      65.1 %    42.0
...
```

### Use from Python

```python
from regix import Regix, RegressionConfig

cfg = RegressionConfig(
    cc_max=15,
    mi_min=20,
    coverage_min=80,
)

rx = Regix(config=cfg, workdir=".")
report = rx.compare("HEAD~1", "HEAD")

for regression in report.regressions:
    print(f"{regression.file}::{regression.symbol}  "
          f"{regression.metric} {regression.before} → {regression.after}  "
          f"({regression.severity})")

if report.has_errors:
    raise SystemExit(1)
```

---

## Core concepts

### Snapshot

A `Snapshot` is an immutable record of all tracked metrics for a codebase at a specific point in time. It is identified by a git ref (commit SHA, branch, tag) or the special value `"local"` for the current working tree.

```python
from regix import Snapshot

snap = Snapshot.from_ref("HEAD", workdir=".")
print(snap.metrics["pyqual/cli.py"]["bulk_run_cmd"]["cc"])  # 19
```

Snapshots are cached by content hash so repeated comparisons are fast.

### Regression

A `Regression` is a detected worsening of a metric between two snapshots, at symbol, module, or project level.

```python
@dataclass
class Regression:
    file: str            # relative path
    symbol: str | None   # function or class name, None = module-level
    line: int | None     # approximate line in the target ref
    metric: str          # "cc", "mi", "coverage", "length", ...
    before: float
    after: float
    delta: float         # after - before (positive = worse for cc/length)
    severity: str        # "error" | "warning" | "info"
    threshold: float     # the configured limit that was crossed
```

### Improvement

An `Improvement` is the mirror of a `Regression` — a metric that got *better*. Regix tracks both so you get a complete picture of a refactoring.

### Report

A `RegressionReport` aggregates all `Regression` and `Improvement` objects from a comparison, plus summary statistics, gate pass/fail status, and the two snapshot refs.

---

## CLI reference

```
regix [OPTIONS] COMMAND [ARGS]

Commands:
  compare   Compare metrics between two git refs or local state.
  history   Show metric timeline across N historical commits.
  snapshot  Capture and store a snapshot without comparing.
  diff      Show symbol-level metric diff (like git diff but for metrics).
  gates     Check current state against configured quality gates.
  report    Re-render a stored comparison as a different format.
```

### `regix compare` 

```
regix compare [REF_A] [REF_B] [OPTIONS]

  REF_A    Base ref (default: HEAD~1)
  REF_B    Target ref (default: HEAD or local if --local)

Options:
  --local              Compare REF_A against the current working tree
  --config FILE        Path to regix.yaml (default: regix.yaml or .regix/config.yaml)
  --format             Output format: rich | json | yaml | toon  [default: rich]
  --output FILE        Write report to file instead of stdout
  --metric TEXT        Only report on specific metric(s), repeatable
  --file TEXT          Only report on specific file(s), repeatable
  --symbol TEXT        Only report on specific function/class, repeatable
  --errors-only        Suppress warnings, show errors only
  --fail-on warning    Exit code 1 on warnings too (default: errors only)
  --no-improvements    Suppress improvement entries from output
  --depth INTEGER      For history mode: number of commits to scan
```

### `regix history` 

```
regix history [OPTIONS]

Options:
  --depth INTEGER      Number of commits to include  [default: 20]
  --ref TEXT           Starting ref  [default: HEAD]
  --metric TEXT        Metrics to include, repeatable
  --file TEXT          Filter to specific file(s)
  --symbol TEXT        Filter to specific symbol
  --format             rich | json | yaml | csv  [default: rich]
  --output FILE
```

### `regix diff` 

```
regix diff [REF_A] [REF_B] [OPTIONS]

  Shows a symbol-by-symbol metric diff, similar to `git diff` but for
  static analysis data instead of source lines.

Options:
  --threshold FLOAT    Only show symbols with delta >= threshold
  --metric TEXT        Filter to specific metric(s)
```

---

## Configuration

Create a `regix.yaml` at the project root:

```yaml
regix:
  workdir: .

  metrics:
    cc_max: 15              # cyclomatic complexity per function
    mi_min: 20              # maintainability index (radon)
    coverage_min: 80        # test coverage (%)
    length_max: 100         # function length in lines
    docstring_min: 60       # docstring coverage (%)

  thresholds:
    delta_warn: 2           # minimum delta to emit a warning
    delta_error: 5          # minimum delta to emit an error

  backends:
    cc: lizard              # lizard | radon | both
    mi: radon
    coverage: pytest-cov
    quality: vallm          # optional LLM-based score

  exclude:
    - "tests/**"
    - "examples/**"
    - "docs/**"
    - "**/migrations/**"

  include:
    - "src/**"
    - "mypackage/**"

  output:
    format: rich            # rich | json | yaml | toon
    show_improvements: true
    max_symbols: 50         # truncate long reports

  gates:
    on_regression: warn     # warn | error | block
    fail_exit_code: 1
```

See [configuration.md](configuration.md) for the full reference.

---

## Integration with CI

### GitHub Actions

```yaml
- name: Check for regressions
  run: |
    pip install "regix[full]"
    regix compare ${{ github.event.pull_request.base.sha }} HEAD \
      --format json --output .regix/report.json
    regix gates --fail-on error
```

### Pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: regix
        name: Regression check
        entry: regix compare HEAD --local --errors-only
        language: python
        pass_filenames: false
```

### pyqual integration

Regix ships a pyqual-compatible stage preset and gate collector:

```yaml
# pyqual.yaml
stages:
  - name: regression-check
    tool: regix
    when: metrics_fail

metrics:
  regression_errors_max: 0
  regression_warnings_max: 5
```

The `regix` preset runs `regix compare HEAD~1 HEAD --format toon --output .regix/` and the gate collector reads `.regix/report.toon.yaml` for `regression_errors` and `regression_warnings` metrics.

---

## Design principles (lessons from pyqual)

These principles were derived from running iterative quality pipelines and observing failure modes:

1. **Fix the measurement before fixing the code.** If the tool counts unsupported files in the pass-rate denominator, the metric is misleading. Regix measures only what it can actually analyse.

2. **Report at symbol granularity, not file granularity.** A file-level CC average of 6.4 masks individual functions with CC 19+. Regix always links a regression to the smallest attributable unit.

3. **Distinguish regression from absolute violation.** A function with CC=18 that was CC=18 last week is not a *new* regression — it is an existing issue. A function that went CC=10 → CC=18 in this PR *is* a regression. Both should be reportable, but separately.

4. **Stagnation is a signal.** If a fix pass runs twice and produces identical metric values, continuing to iterate wastes time. Regix exposes `report.stagnated` so callers can exit early.

5. **Make the improvement visible too.** Refactoring that improves CC from 22 → 14 in three functions while worsening one from 12 → 16 still net-positive. Hiding improvements creates a discouraging feedback loop.

6. **Historical depth is essential.** A single before/after comparison misses the *trend*. The `history` command lets you see that coverage has been falling 1 % per week for six weeks, not just that it is below the gate today.

7. **Output must be machine-readable.** Every report format (JSON, YAML, TOON) is stable and versioned so downstream tools (dashboards, ticket systems, fix agents) can consume regression data programmatically.

---

## Development

### Running tests with tox

Regix uses `tox` for testing across multiple Python versions:

```bash
# Install tox
pip install tox

# Run tests in current Python version
tox -e py313

# Run tests in all supported versions
tox

# Run with coverage, linting, and type checking
tox -e py313-full,lint,type
```

Supported environments: `py39`, `py310`, `py311`, `py312`, `py313`, `lint` (ruff), `type` (mypy).

### Automated quality pipeline (pyqual)

The project includes a `pyqual` pipeline configured in `pyqual.yaml` that automates:

1. **Baseline analysis** — code2llm extraction
2. **Validation** — vallm batch validation
3. **Testing** — pytest with coverage
4. **Regression fixing** — prefact + llx auto-fix
5. **Version bump** — automatic patch version increment
6. **Publishing** — build and upload to PyPI

Run the full pipeline:

```bash
pyqual run -c pyqual.yaml
```

The pipeline loops up to 5 iterations, automatically fixing issues until all quality gates pass:
- CC ≤ 10 per function
- vallm pass rate ≥ 50%
- Test coverage ≥ 80%

---

## Architecture

```
regix/
├── __init__.py          # Public API: Regix, Snapshot, RegressionReport, ...
├── cli.py               # Typer-based CLI (compare, history, diff, gates, ...)
├── config.py            # RegressionConfig dataclass + YAML loader
├── snapshot.py          # Snapshot capture, caching, git checkout logic
├── compare.py           # Core comparison engine: metric deltas + ArchSmell detection
├── history.py           # Multi-commit timeline builder
├── report.py            # Rendering: rich tables, JSON/YAML/TOON serialisation
├── gates.py             # Gate evaluation (pass/fail) from RegressionReport
├── backends/
│   ├── __init__.py
│   ├── lizard_backend.py        # CC + function length via lizard
│   ├── radon_backend.py         # MI + raw metrics via radon
│   ├── coverage_backend.py      # Coverage via pytest-cov / .coverage file
│   ├── docstring_backend.py     # Docstring coverage (AST, built-in)
│   ├── structure_backend.py     # fan_out, call_count, symbol_count (AST, built-in)
│   ├── architecture_backend.py  # Cross-symbol ArchSmell detection
│   └── vallm_backend.py         # LLM quality score via vallm batch
├── git.py               # Git helpers: checkout, worktree, diff, log
├── cache.py             # Content-addressed snapshot cache (~/.cache/regix/)
└── integrations/
    ├── pyqual.py        # pyqual preset + gate collector
    └── github.py        # GitHub Actions annotations formatter
```

See [architecture.md](architecture.md) for a detailed description of each module.

---

## Comparison with related tools

| Tool | What it measures | Regression detection | Git-aware | Symbol-level |
|------|-----------------|---------------------|-----------|--------------|
| **Regix** | CC, MI, coverage, length, quality | ✅ first-class | ✅ | ✅ |
| pylint | Style, errors | ❌ | ❌ | ❌ |
| radon | CC, MI raw | ❌ | ❌ | ✅ |
| lizard | CC, length | ❌ | ❌ | ✅ |
| pytest-cov | Coverage | ❌ | ❌ | ❌ |
| pyqual | Quality gates (pipeline) | partial (gate-level) | ❌ | ❌ |
| diff-cover | Coverage diff | partial (line-level) | ✅ | ❌ |
| xenon | CC thresholds | ❌ | ❌ | ❌ |

Regix is designed to sit **above** analysis tools (lizard, radon, vallm) as the comparison and regression-detection layer, and **alongside** gate tools (pyqual) as a complementary data source.

---

## Roadmap

- [ ] `v0.1` — Core compare/history CLI, lizard + radon backends, JSON/rich output
- [ ] `v0.2` — pytest-cov backend, configuration file, CI presets
- [ ] `v0.3` — vallm backend, pyqual integration preset
- [ ] `v0.4` — Symbol-level caching, incremental snapshots for large repos
- [ ] `v0.5` — Web dashboard (static HTML report), trend charts
- [ ] `v1.0` — Stable API, full docs, PyPI release

---

## License

Licensed under Apache-2.0.
