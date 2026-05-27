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
- **version**: `0.1.25`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, regix/

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

## Dependencies

- **runtime**: pyyaml>=6.0, typer>=0.12, rich>=13.0
- **analysis (optional)**: lizard, radon, coverage[toml], vallm
- **dev/test**: pytest, pytest-cov, tox, ruff, mypy

## Source Map

- tests/test_gates.py
- tests/test_backends.py
- tests/test_history.py
- tests/test_exceptions.py
- tests/conftest.py
- tests/test_report.py
- tests/test_config_full.py
- tests/test_smells.py
- tests/test_git.py
- tests/__init__.py
- tests/test_impact.py
- tests/test_config.py
- tests/test_code2llm_backend.py
- tests/test_benchmark.py
- tests/test_regix_class.py
- tests/test_models.py
- tests/test_cache.py
- tests/test_report_full.py
- tests/test_compare.py
- tests/test_compare_full.py
- tests/test_snapshot.py
- tests/test_cli.py
- tests/test_integrations.py
- tests/test_regix.py
- scripts/check_regression.py
- regix/backends/architecture_backend.py
- regix/backends/base.py
- regix/backends/docstring_backend.py
- regix/backends/radon_backend.py
- regix/backends/vallm_backend.py
- regix/backends/__init__.py
- regix/backends/structure_backend.py
- regix/backends/code2llm_backend.py
- regix/backends/coverage_backend.py
- regix/backends/lizard_backend.py
- regix/config.py
- regix/exceptions.py
- regix/cli.py
- regix/impact.py
- regix/gates.py
- regix/__init__.py
- regix/compare.py
- regix/benchmark/cli.py
- regix/benchmark/reporter.py
- regix/benchmark/__init__.py
- regix/benchmark/__main__.py
- regix/benchmark/models.py
- regix/benchmark/suite.py
- regix/benchmark/factory.py
- regix/benchmark/probes.py

## Intent

- Track code-quality regressions between refs.
- Support LLM patch validation via diff-scoped `regix review`.
- Target selective tests using impact + dependency analysis.
