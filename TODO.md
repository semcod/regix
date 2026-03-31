# TODO

**Updated:** 2026-03-31
**Tests:** 311 passed | **Coverage:** 86% | **Hard-gates:** ✅ all pass

---

## ✅ Completed (this session)

- [x] Refactored `regix.yaml` → nested `gates.hard` / `gates.target` / `deltas` sections
- [x] Added `GateThresholds` dataclass + `GATE_METRICS` single source of truth
- [x] Backward-compat aliases (`cfg.cc_max` → `cfg.hard.cc`) as properties
- [x] Updated `from_dict` parser: new + legacy format support
- [x] Updated `pyproject.toml` to `[tool.regix.gates.hard]` / `[tool.regix.gates.target]`
- [x] Refactored `config.py:from_dict` CC=44 → CC=8 (extracted `_parse_*` helpers)
- [x] Fixed `cache.py:lookup()` — returned `__code__` object (LLM hallucination bug)
- [x] Fixed `report.py` pre-existing f-string syntax error
- [x] Added docstrings to all backend classes (docstring_coverage 0% → 100%)
- [x] All hard-gates pass, 0 errors

## 🔴 Regix Quality — target-gate warnings (27)

These don't block CI but should be improved over time.

### Docstring coverage < 80% (target)
- [ ] regix/backends/architecture_backend.py — 25% (add docstrings to private helpers)
- [ ] regix/backends/coverage_backend.py — 25% (add docstrings to public methods)
- [ ] regix/backends/structure_backend.py — 67% (add docstrings to `_CallVisitor`)
- [ ] regix/config.py — 23% (add docstrings to `_parse_*` static methods)
- [ ] regix/compare.py — 27% (add docstrings to helper functions)
- [ ] regix/smells.py — 56% (add docstrings to detection functions)
- [ ] regix/models.py — 76% (close to target, needs a few more)

### CC > 10 (target ≤ 10)
- [ ] regix/backends/architecture_backend.py:collect — CC=19 (split AST walk into helpers)
- [ ] regix/backends/docstring_backend.py:collect — CC=14 (extract node visitor)
- [ ] regix/backends/radon_backend.py:collect — CC=11 (extract source reading)
- [ ] regix/benchmark.py — multiple functions CC=11-17 (extract probe builders)
- [ ] regix/smells.py — detect functions CC=13-17 (split per-smell detectors)

### MI < 30 (target ≥ 30)
- [ ] regix/backends/architecture_backend.py — MI=17.7
- [ ] regix/smells.py — MI=25.7

## 📋 Code quality (prefact)

### Dependencies
- [ ] pyproject.toml — Outdated: typer 0.23.1 → 0.24.1, rich 13.7.1 → 14.3.3

### Unused `from __future__ import annotations`
- [ ] Remove from: `backends/__init__.py`, `architecture_backend.py`, `coverage_backend.py`, `docstring_backend.py`, `lizard_backend.py`, `radon_backend.py`, `structure_backend.py`, `vallm_backend.py`, `benchmark.py`, `cache.py`, `cli.py`, `compare.py`, `config.py`, `exceptions.py`, `gates.py`, `git.py`, `history.py`, `integrations/__init__.py`, `models.py`, `report.py`, `smells.py`, `snapshot.py`

### Duplicate imports (lazy imports in try/except)
- [ ] regix/backends/lizard_backend.py — `lizard` imported multiple times
- [ ] regix/backends/radon_backend.py — `radon` imported multiple times
- [ ] regix/benchmark.py — `shutil`, `RegressionConfig` duplicated
- [ ] regix/cli.py — `capture`, `do_compare` duplicated

### Magic numbers
- [ ] regix/__init__.py:94, cli.py:81, cli.py:135, cli.py:245, benchmark.py:364, git.py:52

### Missing return type annotations
- [ ] regix/cli.py — `diff`, `gates`, `status` missing `-> None`

## 🚀 Feature improvements

- [ ] `regix gates` — show file:symbol for each violation (not just metric name)
- [ ] `regix gates` — add `--format json` output for CI integration
- [ ] `regix init` — generate new-style `gates.hard`/`gates.target` config
- [ ] Parallel backend execution (`backends_parallel: true` is defined but not implemented)
- [ ] Coverage backend — integrate with pytest-cov in-memory (currently reads `.coverage` files)
- [ ] History — add trend visualization (sparklines in terminal)

---

*Run: `prefact -a --execute-todos` | `regix gates` | `pyqual run`*