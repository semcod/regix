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
- **version**: `0.1.12`
- **python_requires**: `>=3.13`
- **license**: MIT
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, src/

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

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
- .tox/py313/lib/python3.13/site-packages/_virtualenv.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/inline.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/__init__.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/linkify.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/state_core.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/smartquotes.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/block.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/normalize.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/text_join.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_core/replacements.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/fragments_join.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/entity.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/newline.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/backticks.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/html_inline.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/__init__.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/linkify.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/link.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/escape.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/emphasis.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/balance_pairs.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/state_inline.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/image.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/strikethrough.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/autolink.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/rules_inline/text.py
- .tox/py313/lib/python3.13/site-packages/markdown_it/presets/zero.py
