# regix

Regression Index — detect and measure code quality regressions between git versions

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Dependencies](#dependencies)
- [Source Map](#source-map)
- [Intent](#intent)

## Metadata

- **name**: `regix`
- **version**: `0.1.24`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, regix/

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

## Dependencies

- **runtime**: `pyyaml>=6.0`, `typer>=0.12`, `rich>=13.0`
- **analysis (optional)**: `lizard>=1.17`, `radon>=6.0`, `coverage[toml]>=7.0`, `vallm>=0.1`
- **dev/test**: `pytest>=8.0`, `pytest-cov>=5.0`, `mypy`, `ruff`, `tox`

## Source Map

- regix/cli.py
- regix/compare.py
- regix/config.py
- regix/git.py
- regix/history.py
- regix/impact.py
- regix/models.py
- regix/report.py
- regix/smells.py
- regix/snapshot.py
- regix/backends/architecture_backend.py
- regix/backends/structure_backend.py
- regix/backends/lizard_backend.py
- regix/backends/radon_backend.py
- regix/backends/coverage_backend.py
- regix/backends/docstring_backend.py
- regix/backends/vallm_backend.py
- tests/test_cli.py
- tests/test_compare.py
- tests/test_git.py
- tests/test_smells.py
- tests/test_snapshot.py
- tests/test_report.py
- tests/test_backends.py
- tests/test_history.py

## Intent

- Track code-quality regressions between refs, not only absolute threshold violations.
- Provide diff-scoped LLM regression gating via `regix review`.
- Use dependency-aware impact analysis (`regix impact`) to run only relevant tests.
- Emit machine-readable outputs for CI, quality gates, and automation loops.
