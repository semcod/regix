# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.10] - 2026-04-07

### Fixed
- Fix string-concat issues (ticket-06d47ed2)
- Fix unused-imports issues (ticket-4fb302bf)
- Fix string-concat issues (ticket-fc0ad061)
- Fix unused-imports issues (ticket-1fee0f0c)
- Fix wildcard-imports issues (ticket-94255818)
- Fix ai-boilerplate issues (ticket-b9f41270)
- Fix ai-boilerplate issues (ticket-16a8fa4b)

## [0.1.10] - 2026-03-31

### Fixed
- Fix string-concat issues (ticket-57e00386)
- Fix unused-imports issues (ticket-61231e5d)
- Fix duplicate-imports issues (ticket-b6ae509a)
- Fix magic-numbers issues (ticket-e44c3780)
- Fix ai-boilerplate issues (ticket-053eeda2)

## [0.1.10] - 2026-03-31

### Fixed
- Fix unused-imports issues (ticket-0bde17f3)
- Fix string-concat issues (ticket-6db3468c)
- Fix unused-imports issues (ticket-e5c3279d)
- Fix unused-imports issues (ticket-c101a5d4)
- Fix duplicate-imports issues (ticket-5b111a30)
- Fix magic-numbers issues (ticket-3e9e5089)
- Fix unused-imports issues (ticket-d2062800)
- Fix unused-imports issues (ticket-69e5d148)
- Fix duplicate-imports issues (ticket-17e7ab71)
- Fix unused-imports issues (ticket-cc15ce69)
- Fix duplicate-imports issues (ticket-8628573d)
- Fix string-concat issues (ticket-258ef67d)
- Fix unused-imports issues (ticket-c4827859)
- Fix unused-imports issues (ticket-7368f1b0)
- Fix string-concat issues (ticket-6382eedf)
- Fix unused-imports issues (ticket-c22fdecd)
- Fix smart-return-type issues (ticket-4fc3119c)
- Fix unused-imports issues (ticket-32e4b358)
- Fix duplicate-imports issues (ticket-c940fe15)
- Fix magic-numbers issues (ticket-ef8db94a)
- Fix ai-boilerplate issues (ticket-030c3bda)
- Fix unused-imports issues (ticket-9727732c)
- Fix unused-imports issues (ticket-92d71d68)
- Fix unused-imports issues (ticket-82568973)
- Fix duplicate-imports issues (ticket-1630346c)
- Fix magic-numbers issues (ticket-582e504d)
- Fix string-concat issues (ticket-2e46383f)
- Fix unused-imports issues (ticket-3a01a30a)
- Fix magic-numbers issues (ticket-f8ad41ba)
- Fix unused-imports issues (ticket-9f496964)
- Fix unused-imports issues (ticket-c416f3b1)
- Fix unused-imports issues (ticket-816aeaae)
- Fix string-concat issues (ticket-5bbc452f)
- Fix unused-imports issues (ticket-958ddbeb)
- Fix string-concat issues (ticket-de373714)
- Fix unused-imports issues (ticket-fe79d7ce)
- Fix string-concat issues (ticket-20155b8a)
- Fix unused-imports issues (ticket-2054d593)
- Fix unused-imports issues (ticket-3dc7c36c)
- Fix smart-return-type issues (ticket-89e7133c)
- Fix ai-boilerplate issues (ticket-576e3028)

## [Unreleased]

### Added
- Added `tox.ini` for multi-Python testing (py39-py313, lint, type)
- Added `bump_version` stage to `pyqual.yaml` for automatic version increment before publish
- Added Development section to README.md documenting tox and pyqual pipeline

### Changed
- Updated `pyqual.yaml` publish stage to use pre-bumped version from VERSION file

## [0.1.12] - 2026-04-07

### Docs
- Update CHANGELOG.md
- Update README.md
- Update TODO.md

### Test
- Update tests/conftest.py
- Update tests/test_backends.py
- Update tests/test_benchmark.py
- Update tests/test_code2llm_backend.py
- Update tests/test_config.py
- Update tests/test_config_full.py
- Update tests/test_exceptions.py
- Update tests/test_gates.py
- Update tests/test_history.py
- Update tests/test_integrations.py
- ... and 2 more files

### Other
- Update planfile.yaml
- Update regix/backends/__init__.py
- Update regix/backends/code2llm_backend.py
- Update regix/benchmark.py
- Update regix/cli.py
- Update regix/config.py
- Update regix/models.py
- Update regix/smells.py

## [0.1.7] - 2026-03-31

### Docs
- Update CHANGELOG.md
- Update README.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_backends.py

### Other
- Update planfile.yaml
- Update project.sh
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/compact_flow.mmd
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- Update project/index.html
- Update project/map.toon.yaml
- Update project/project.toon.yaml
- ... and 18 more files

## [0.1.6] - 2026-03-31

### Docs
- Update README.md

### Test
- Update tests/conftest.py

### Other
- Update Makefile

## [0.1.5] - 2026-03-31

### Docs
- Update BENCHMARK.md
- Update README.md

### Other
- Update Makefile
- Update project.sh
- Update pyqual.yaml
- Update regix/__init__.py
- Update regix/backends/__init__.py
- Update regix/backends/architecture_backend.py
- Update regix/backends/coverage_backend.py
- Update regix/backends/docstring_backend.py
- Update regix/backends/lizard_backend.py
- Update regix/backends/radon_backend.py
- ... and 5 more files

## [0.1.4] - 2026-03-31

### Docs
- Update CHANGELOG.md
- Update README.md
- Update TODO.md
- Update docs/README.md
- Update docs/architecture.md
- Update docs/configuration.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_smells.py

### Other
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- Update project/flow.png
- ... and 15 more files

## [0.1.3] - 2026-03-31

### Docs
- Update README.md

### Other
- Update regix/compare.py

## [0.1.2] - 2026-03-31

### Docs
- Update README.md
- Update docs/README.md
- Update docs/algitex.md
- Update docs/code2docs.md
- Update docs/code2llm.md
- Update docs/costs.md
- Update docs/devloop.md
- Update docs/ecosystem.md
- Update docs/llx.md
- Update docs/planfile.md
- ... and 4 more files

## [0.1.1] - 2026-03-31

### Docs
- Update README.md
- Update TODO.md
- Update docs/api.md
- Update docs/architecture.md
- Update docs/configuration.md
- Update docs/index.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/__init__.py
- Update tests/test_backends.py
- Update tests/test_compare.py
- Update tests/test_config.py
- Update tests/test_models.py
- Update tests/test_regix.py
- Update tests/test_report.py

### Other
- Update .gitignore
- Update LICENSE
- Update planfile.yaml
- Update prefact.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- ... and 28 more files

