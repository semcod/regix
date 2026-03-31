# Regix — Architecture

## Overview

Regix is structured as a thin orchestration layer over existing static analysis tools. It does not reimplement code analysis — instead it coordinates snapshot capture, metric comparison, and report generation.

```
┌─────────────────────────────────────────────────────────────┐
│                        User / CI                            │
│           CLI (regix compare ...)  │  Python API (Regix())  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Regix core                              │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Snapshot    │  │  Compare     │  │  History         │  │
│  │  capture     │  │  engine      │  │  timeline        │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                   │             │
│         ▼                 ▼                   ▼             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Cache layer                        │   │
│  │   content-addressed by (commit_sha, backend_versions)│   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │  lizard    │ │   radon    │ │  pytest-cov│  ...backends
   │  (CC/len)  │ │   (MI)     │ │ (coverage) │
   └────────────┘ └────────────┘ └────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │   git.py   │ │  Report    │ │  Gates     │
   │ worktree / │ │  renderer  │ │  evaluator │
   │ stash mgr  │ │            │ │            │
   └────────────┘ └────────────┘ └────────────┘
```

---

## Module descriptions

### `regix/__init__.py`

Public API surface. Exports `Regix`, `Snapshot`, `RegressionReport`, `Regression`, `Improvement`, `RegressionConfig`, `SymbolMetrics`, `MetricDelta`. Nothing in `__init__.py` contains logic — it only imports from the submodules.

---

### `regix/config.py`

**`RegressionConfig`** — a frozen dataclass holding all user-configurable values. Loaded from YAML via `from_file()` or constructed directly.

Design decision: all thresholds live in a single config object rather than scattered across backends. This means a backend does not decide what is a "regression" — the `compare.py` engine does, using the thresholds from `RegressionConfig`.

```python
# How severity is decided (in compare.py, not backends)
delta = after - before   # for CC, length, imports: positive = worse
if delta >= config.delta_error:
    severity = "error"
elif delta >= config.delta_warn:
    severity = "warning"
```

The `exclude`/`include` glob patterns are evaluated in `snapshot.py` before any backend runs so excluded files are never analysed.

---

### `regix/snapshot.py`

**`Snapshot`** — the core data structure. Immutable (frozen dataclass), hashable by `(commit_sha, backend_versions_hash)`.

Capture flow:

```
Snapshot.from_ref(ref)
    │
    ├─► resolve_ref(ref)       → commit SHA
    ├─► cache.lookup(sha, ...)  → cache hit? return cached snapshot
    │
    ├─► checkout_temporary(ref) (if ref != "local")
    │       └─► git worktree add /tmp/regix_<sha>
    │
    ├─► collect files matching include/exclude patterns
    │
    ├─► for each backend:
    │       backend.collect(worktree_path, files, config) → [SymbolMetrics]
    │
    ├─► merge SymbolMetrics lists into Snapshot
    ├─► cache.store(snapshot)
    └─► return snapshot
```

**Why `git worktree add` instead of `git checkout`?**

`git checkout` modifies the working tree and HEAD, which:
- Is destructive if the user has uncommitted changes
- Is slow (the user's IDE re-indexes the tree)
- Races with other processes reading the repo

`git worktree add` creates a second working tree in a temp directory without touching the original. It is fast, non-destructive, and safe for concurrent use. The worktree is removed with `git worktree remove` after collection.

For the `"local"` ref, no git operations are performed — the analysis runs directly on `workdir`. This allows regression-checking a dirty working tree against a committed baseline.

---

### `regix/compare.py`

The core comparison engine. Takes two `Snapshot` objects and produces a `RegressionReport`.

Algorithm:

```
compare(snap_before, snap_after)
    │
    ├─► build symbol index: {(file, symbol) → SymbolMetrics} for each snapshot
    │
    ├─► for each (file, symbol) in union of both indexes:
    │       │
    │       ├─► m_before = snap_before.get(file, symbol)  (None if new)
    │       ├─► m_after  = snap_after.get(file, symbol)   (None if deleted)
    │       │
    │       └─► for each metric in [cc, mi, coverage, length, ...]:
    │               delta = compute_delta(metric, m_before, m_after)
    │               if is_regression(metric, delta, config):
    │                   emit Regression(severity=..., ...)
    │               elif is_improvement(metric, delta):
    │                   emit Improvement(...)
    │
    └─► return RegressionReport(regressions, improvements, ...)
```

**New symbols** (appear in `after` but not `before`): not reported as regression, even if their CC exceeds the threshold. That is a gate violation (absolute), not a regression (relative). Use `regix.gates` for absolute checks.

**Deleted symbols** (in `before` but not `after`): reported as implicit improvements for all metrics (symbol was removed, reducing the metric contribution).

**Metric direction convention:**

| Metric | Direction | Regression when delta |
|---|---|---|
| `cc` | lower is better | delta > 0 |
| `length` | lower is better | delta > 0 |
| `imports` | lower is better | delta > 0 |
| `mi` | higher is better | delta < 0 |
| `coverage` | higher is better | delta < 0 |
| `docstring_coverage` | higher is better | delta < 0 |
| `quality_score` | higher is better | delta < 0 |

---

### `regix/history.py`

Builds a `HistoryReport` by calling `Snapshot.from_ref()` for each commit in the walk, then calling `compare.py` between consecutive pairs.

The history walk uses the snapshot cache heavily — most commits in a deep history scan will already be cached from previous runs.

**Stagnation detection** within history: if a metric value is identical across three or more consecutive commits, the `TrendLine` marks those commits as `stagnant` and stops reporting them as individual regressions (they are old, not new).

**Trend computation**: a simple linear regression (`slope = covariance(x, y) / variance(x)`) over the last N values. A positive slope for a "lower is better" metric means the metric is degrading over time.

---

### `regix/report.py`

Rendering layer. Takes a `RegressionReport` or `HistoryReport` and produces formatted output. Contains no business logic.

| Format | Class | Notes |
|---|---|---|
| `rich` | `RichRenderer` | Uses `rich.table`, `rich.console` |
| `json` | `JsonRenderer` | Stable schema, versioned |
| `yaml` | `YamlRenderer` | PyYAML, human-friendly |
| `toon` | `ToonRenderer` | Machine-readable plain text, compatible with pyqual |

The TOON format is a deliberate design choice: it is readable without a JSON parser, greppable, and produces stable diffs in git. It was designed for use in systems (like pyqual) that parse tool output with regex rather than structured deserialisers.

**Report schema version**: the JSON/YAML output includes a top-level `"regix_schema_version": "1"` field so consumers can detect breaking schema changes.

---

### `regix/gates.py`

Evaluates absolute quality gates (threshold checks) against a single snapshot. Does not require a comparison — it answers "does this snapshot meet the configured standards?" rather than "did this snapshot *regress* relative to the previous one?"

Used by `regix gates` CLI command and by the pyqual integration.

The separation between `gates.py` (absolute) and `compare.py` (relative/delta) was a key lesson from pyqual: a function with CC=18 that was CC=18 last week is a **gate violation** (requires refactoring) but not a **regression** (did not get worse in this change). Mixing the two concepts produces noisy reports where a PR touching an already-bad file is flagged for something it didn't cause.

---

### `regix/git.py`

Pure git utility functions. No Regix-specific logic. Calls `git` via `subprocess.run`.

Key design choice: **`git worktree add`** for multi-ref analysis rather than stash/checkout. This avoids the class of bugs seen in simpler implementations where:
- A tool catches SIGINT during checkout and leaves the repo in a detached HEAD state.
- Two parallel CI jobs analyse the same repo simultaneously.
- The IDE reindexes the working tree mid-analysis.

Worktree lifecycle:

```python
worktree_path = Path(tempfile.mkdtemp(prefix="regix_"))
subprocess.run(["git", "worktree", "add", str(worktree_path), sha])
try:
    yield worktree_path
finally:
    subprocess.run(["git", "worktree", "remove", "--force", str(worktree_path)])
    worktree_path.rmdir()
```

---

### `regix/cache.py`

Content-addressed snapshot cache stored in `~/.cache/regix/` (XDG-compliant, respects `XDG_CACHE_HOME`).

Cache key: `sha256(commit_sha + ":" + json.dumps(sorted(backend_versions.items())))`.

Each cached snapshot is a gzip-compressed JSON file. Cache entries are never invalidated automatically (a commit SHA is immutable). The cache can be cleared with `regix cache clear`.

For the `"local"` ref, caching is disabled — the working tree may change between calls.

**Why cache?** A deep history scan (20 commits × 4 backends × 100 files) can take several minutes. Caching makes repeated `regix history` calls instant for already-analysed commits.

---

### `regix/backends/`

Each backend is a self-contained module. Backends have no dependencies on each other and no dependencies on `compare.py` or `history.py`. They only know about `SymbolMetrics`, `RegressionConfig`, and the path to analyse.

**`lizard.py`** — Runs `lizard --xml` on the file list, parses the XML to extract `cc` and function `length` per symbol.

**`radon.py`** — Runs `radon mi --json` (maintainability index) and `radon cc --json` (raw CC). The lizard CC is preferred over radon CC when both are configured, but they can be run simultaneously for cross-validation.

**`coverage.py`** — Reads a `.coverage` SQLite file (produced by `pytest --cov`) using `coverage.py`'s public API. Extracts per-file line coverage percentages. Does not run pytest itself — it only reads existing coverage data.

**`vallm.py`** — Runs `vallm batch <workdir> --recursive --format json` and parses the JSON output for per-file quality scores. To avoid double-scanning, `vallm.py` only scans files that match the `include` patterns.

**`docstring.py`** — Pure Python, no subprocess. Uses the `ast` module to count functions/classes with and without docstrings. Fast enough to run on every file without caching.

---

## Data flow diagram

```
                         regix compare HEAD~1 HEAD
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
             Snapshot(HEAD~1)                  Snapshot(HEAD)
                    │                                 │
         ┌──────────┴──────────┐         ┌────────────┴───────────┐
         │  git worktree add   │         │  git worktree add      │
         │  /tmp/regix_abc123  │         │  /tmp/regix_def456     │
         └──────────┬──────────┘         └────────────┬───────────┘
                    │                                 │
         ┌──────────┴──────────┐         ┌────────────┴───────────┐
         │  lizard collect     │         │  lizard collect        │
         │  radon collect      │         │  radon collect         │
         │  coverage collect   │         │  coverage collect      │
         └──────────┬──────────┘         └────────────┬───────────┘
                    │                                 │
         [SymbolMetrics list]             [SymbolMetrics list]
                    │                                 │
                    └──────────────┬──────────────────┘
                                   ▼
                          compare engine
                                   │
                          RegressionReport
                                   │
                    ┌──────────────┴──────────────────┐
                    ▼                                 ▼
             RichRenderer                        JsonRenderer
                    │                                 │
          (terminal output)              .regix/report.json
```

---

## Threading and concurrency

Snapshot captures for different refs are independent and can run in parallel. The `history.py` module uses `concurrent.futures.ThreadPoolExecutor` with a configurable `max_workers` (default: 4) to parallelise snapshot capture across commits.

The cache layer uses file-level locking (`fcntl.flock`) to prevent concurrent writes to the same cache entry.

Backend processes (`lizard`, `radon`, `vallm`) are spawned as subprocesses. Each subprocess call uses `subprocess.run` (blocking). Within a single snapshot capture, backends run sequentially by default. Set `regix.backends.parallel = true` in config to run them concurrently (useful for large repos with many backends).

---

## Error handling philosophy

Errors are surfaced as typed exceptions (see `api.md`) rather than printed messages. The CLI catches exceptions at the top level and formats them for the user. This means library users get structured error information they can handle programmatically.

Backend errors are non-fatal by default: if lizard fails on a file, the CC metrics for that file are `None` rather than crashing the whole snapshot. A `BackendError` is only raised if the backend fails to produce *any* output (e.g., the binary is not installed).

---

## Extension points

1. **Custom backends** — implement `BackendBase` and call `register_backend()`.
2. **Custom renderers** — implement `RendererBase` and pass `renderer=MyRenderer()` to report methods.
3. **Custom metric directions** — pass `metric_directions={"mymetic": "lower"}` to `RegressionConfig`.
4. **Post-comparison hooks** — pass `on_regression=callback` to `Regix()` to receive `Regression` objects as they are produced.
5. **pyqual integration** — use `regix.integrations.pyqual` (see `api.md`).
