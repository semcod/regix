# Regix Documentation

**Regix** — Regression Index for Python code quality.

Detects, measures and reports code quality regressions between git versions at function, class and line granularity.

---

## Documents

| Document | Description |
|---|---|
| [README.md](README.md) | Overview, quick start, CLI reference, design principles |
| [api.md](api.md) | Full Python API: `Regix`, `Snapshot`, `RegressionReport`, backends, git helpers |
| [architecture.md](architecture.md) | Module layout, data flow, design decisions, extension points |
| [configuration.md](configuration.md) | `regix.yaml` / `pyproject.toml` full reference, threshold tuning, common configs |
| [pyproject.toml](pyproject.toml) | Library scaffold ready to copy as a new repo root |

---

## Origin

This documentation was designed based on operational experience with the [pyqual](../README.md) iterative quality-gate pipeline. The key lessons that shaped Regix:

- A vallm scan of an entire project root (including `docs/`, `examples/`, `*.yaml`) counted 39 unsupported files in the denominator, dropping `vallm_pass` from ~98% to 58.3%. → **Regix only analyses files it can actually measure.**
- The fix loop ran 3 iterations with identical gate values because the fix tool was targeting style issues in `examples/` while the failing gates were about CC in core source files. → **Regix links every regression to the exact symbol that caused it, so the fix is targeted.**
- `fix_result: unknown` appeared in every run summary because the output parser looked for "N files changed" summary lines, but `llx fix --verbose` outputs raw unified diff (`+++ b/file`). → **Regix detects changes by counting `+++ b/` diff lines, not by parsing prose summaries.**
- The stagnation-detection method `_iteration_stagnated` existed as a dead stub in the pipeline for several versions before the loop actually called it. → **Regix makes stagnation a first-class concept with `report.stagnated` and a configurable `stagnation_window`.**
- High-CC functions (CC=19–26) were invisible in the overall `cc_avg=6.4` gate because the average masked individual outliers. → **Regix reports at symbol granularity, not file averages.**
