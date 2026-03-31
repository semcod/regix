# Regix — Regression Index for Python Code Quality


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.1-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.15-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-2.0h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $0.1500 (1 commits)
- 👤 **Human dev:** ~$200 (2.0h @ $100/h, 30min dedup)

Generated on 2026-03-31 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---

**Regix** is a Python library for detecting, measuring, and reporting code quality regressions between versions of a codebase. It compares static analysis metrics across git commits, branches, or local snapshots and pinpoints exactly which functions, classes, or lines have regressed — and by how much.

> Inspired by operational experience with [pyqual](https://github.com/semcod/pyqual): iterative quality-gate pipelines revealed that without structured regression tracking, metric changes across refactoring cycles are invisible until a gate breaks.

---

## Problem statement

When refactoring code over multiple iterations:

- A function's cyclomatic complexity improves in one commit, then regresses two commits later.
- Test coverage drops by 3% after a merge — but no single file is obviously responsible.
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
- **Multiple backends**: lizard (CC), radon (MI), pytest-cov (coverage), vallm (LLM quality).
- **Machine-readable output**: JSON, YAML, or TOON format for CI integration.
- **Human-readable output**: rich terminal tables and diff-style reports.
- **Zero false-positives mode**: only report regressions that cross a configured threshold delta.

---

## Installation

```bash
pip install regix
```

With optional backends:

```bash
pip install "regix[full]"      # lizard + radon + vallm + pytest-cov
pip install "regix[lizard]"    # CC + length analysis only
pip install "regix[coverage]"  # pytest-cov integration only
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

Summary: 1 error(s), 1 warning(s), 0 improvement(s)
Gates: ✗ FAIL
```

### Compare two branches

```bash
regix compare main feature/refactor --format json > regression.json
```

### Check before committing

```bash
regix compare HEAD --local
```

### Track regressions over last 10 commits

```bash
regix history --depth 10 --metric cc --metric coverage
```

### Use from Python

```python
from regix import Regix, RegressionConfig

cfg = RegressionConfig(cc_max=15, delta_error=5)
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
regix compare [REF_A] [REF_B]    Compare metrics between two git refs
regix history [--depth N]         Show metric timeline across commits
regix snapshot [REF]              Capture and store a snapshot
regix diff [REF_A] [REF_B]       Symbol-level metric diff
regix gates                       Check against absolute quality gates
regix status                      Show config and backend availability
regix init                        Create a default regix.yaml
```

---

## Configuration

Create `regix.yaml` at the project root, or add `[tool.regix]` to `pyproject.toml`:

```yaml
regix:
  metrics:
    cc_max: 15
    mi_min: 20
    coverage_min: 80
  thresholds:
    delta_warn: 2
    delta_error: 5
  backends:
    cc: lizard
    mi: radon
    coverage: pytest-cov
  exclude:
    - "tests/**"
    - "examples/**"
  output:
    format: rich
    dir: .regix/
  gates:
    on_regression: warn
```

---

## CI Integration

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
repos:
  - repo: local
    hooks:
      - id: regix
        name: Regression check
        entry: regix compare HEAD --local --errors-only
        language: python
        pass_filenames: false
```

---

## Design principles

1. **Fix the measurement before fixing the code.** Regix measures only what it can actually analyse.
2. **Report at symbol granularity.** A file-level average of CC=6.4 masks individual functions with CC=19+.
3. **Distinguish regression from absolute violation.** CC=18 that was CC=18 last week is an existing issue, not a new regression.
4. **Stagnation is a signal.** If metrics are identical across iterations, continuing wastes time.
5. **Make improvements visible too.** Hiding improvements creates a discouraging feedback loop.
6. **Historical depth is essential.** A single before/after comparison misses the trend.
7. **Output must be machine-readable.** JSON, YAML, TOON — all stable and versioned.

---

## Architecture

```
regix/
├── __init__.py          # Public API: Regix, Snapshot, RegressionReport
├── cli.py               # Typer CLI (compare, history, diff, gates, ...)
├── config.py            # RegressionConfig + YAML/TOML loader
├── models.py            # Snapshot, Regression, Improvement, Report, etc.
├── snapshot.py          # Snapshot capture, git worktree, file collection
├── compare.py           # Core comparison engine
├── history.py           # Multi-commit timeline builder
├── report.py            # Rendering: rich, JSON, YAML, TOON
├── gates.py             # Absolute gate evaluation
├── cache.py             # Content-addressed snapshot cache
├── git.py               # Git helpers: worktree, ref resolution, diff
├── exceptions.py        # Typed exceptions
├── backends/
│   ├── __init__.py      # BackendBase ABC + registry
│   ├── lizard_backend.py
│   ├── radon_backend.py
│   ├── coverage_backend.py
│   ├── docstring_backend.py
│   └── vallm_backend.py
└── integrations/
    └── __init__.py      # pyqual preset + gate collector
```

---

## Ecosystem

Regix is part of the **semcod/wronai** AI-assisted development toolchain:

| Package | Role |
|---|---|
| **code2llm** | Static analysis engine |
| **vallm** | LLM code validator |
| **regix** | Regression detection layer |
| **devloop** | Declarative pipeline runner |
| **planfile** | Universal ticket standard |
| **llx** | Intelligent LLM router |
| **proxym** | Dashboard layer |
| **costs** | AI cost tracker |

---

## License

Licensed under Apache-2.0.
