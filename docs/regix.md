---
title: "regix: Detecting Code Quality Regressions Between Git Versions"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Code Quality, Regression Testing]
tags: [regix, wronai, semcod, regression, git, cyclomatic-complexity, python]
excerpt: "regix compares static analysis metrics across git commits and pinpoints exactly which functions regressed — and by how much. It answers the question linters cannot: is this code better or worse than before?"
---

# regix: Detecting Code Quality Regressions Between Git Versions

Standard linters tell you what is wrong *now*. They report the current state — cyclomatic complexity is 19, coverage is 72%, maintainability index is 34. What they do not tell you is whether these numbers are *better or worse* than they were before your changes.

**regix** (Regression Index) answers that question. It compares static analysis metrics between any two git refs — commits, branches, tags — and produces a symbol-level regression report showing exactly which functions, classes, or modules got worse, which improved, and by how much.

## Current status

regix v0.1.0 is built and tested: 2,418 lines of source across 20 Python modules, 602 lines of tests across 5 test files, with all 49 tests passing. The library includes a full Typer CLI, pluggable backend system (lizard, radon, coverage, vallm, docstring), content-addressed snapshot caching, and four output formats (rich terminal, JSON, YAML, TOON).

```bash
pip install regix  # coming to PyPI
```

## The core insight

A function with CC=18 that was CC=18 last week is **technical debt** — it needs refactoring, but it is not a regression introduced by recent changes. Reporting it as a regression on every PR creates alert fatigue and causes developers to ignore the tool.

regix separates these two concerns:

- `regix compare` reports **regressions** — delta-based, relative to a baseline
- `regix gates` reports **absolute violations** — threshold-based, point-in-time

Use both: `regix gates` in CI to prevent new violations, and `regix compare` on PRs to catch regressions introduced by specific changes.

## What it tracks

regix monitors seven metrics at function/class/module granularity:

Cyclomatic complexity (lower is better), maintainability index (higher is better), test coverage (higher is better), function length (lower is better), docstring coverage (higher is better), LLM quality score via vallm (higher is better), and import count (lower is better).

Each metric has configurable warn and error thresholds. A delta below the warn threshold is silently ignored — small fluctuations are normal and not worth reporting.

## Usage

```bash
# Compare HEAD against previous commit
regix compare HEAD~1 HEAD

# Compare before committing (working tree vs HEAD)
regix compare HEAD --local

# JSON output for CI
regix compare main feature/refactor --format json > regression.json

# Track trends across last 20 commits
regix history --depth 20
```

From Python:

```python
from regix import Regix

rx = Regix(workdir=".")
report = rx.compare("HEAD~1", "HEAD")

for r in report.regressions:
    print(f"{r.file}::{r.symbol}  {r.metric} {r.before}→{r.after} ({r.severity})")
```

## Architecture highlights

**Git worktree isolation.** regix never modifies your working tree. For non-local comparisons, it uses `git worktree add` to create temporary checkouts in temp directories. Your IDE does not re-index, parallel CI jobs do not conflict, and SIGINT during analysis does not leave the repo in a broken state.

**Backend plugin system.** Each analysis tool (lizard, radon, coverage, vallm) is a self-contained backend implementing a simple ABC: `is_available()`, `collect()`, `version()`. Custom backends can be registered with `register_backend()`.

**Content-addressed caching.** Snapshots are cached by `sha256(commit_sha + backend_versions)`. A deep history scan across 20 commits with 4 backends is slow the first time — and instant on subsequent runs.

**Stagnation detection.** If a metric is identical across three consecutive iterations in a fix loop, regix marks the report as `stagnated` so callers (like devloop) can exit early instead of wasting compute.

## Ecosystem role

regix sits above analysis tools (lizard, radon, vallm) as the comparison layer, and alongside gate tools (devloop) as a complementary data source. It is designed so that:

- **devloop** can invoke regix as a pipeline stage to check for regressions between fix iterations
- **planfile** can import regix regression reports as tickets
- **proxym** can display regression trends on a dashboard
- The pyqual integration preset lets regix act as a drop-in gate collector

## What's next

The v0.2 roadmap includes pytest-cov backend activation, pyproject.toml configuration, and CI presets for GitHub Actions and pre-commit hooks. v0.3 will add the vallm backend and full pyqual integration.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Source: [github.com/semcod/regix](https://github.com/semcod/regix).*
