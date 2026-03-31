---
title: "vallm: LLM-Powered Code Validation at Scale"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Code Quality, Validation]
tags: [vallm, wronai, semcod, llm, code-quality, pypi, python]
excerpt: "vallm uses LLMs to validate code against quality rules — naming conventions, docstring presence, import hygiene, and structural patterns — in batch mode across entire codebases. Published on PyPI."
---

# vallm: LLM-Powered Code Validation at Scale

Traditional linters check syntax and style. Static analyzers measure complexity. But neither understands whether a function name actually describes what it does, whether a docstring is meaningful rather than just present, or whether the code structure follows project conventions that no rule file captures.

**vallm** fills this gap. It uses LLMs to validate code files against quality criteria that go beyond what rule-based tools can express, then produces machine-readable pass/fail scores per file.

## Current status

vallm is **published on PyPI** and actively used within the WronAI ecosystem. It serves as the quality scoring backend for both devloop pipeline gates and regix regression tracking.

```bash
pip install vallm
```

## What it does

vallm operates in batch mode: point it at a directory, and it processes every supported file, producing a quality score (0–1) per file along with specific issue annotations.

```bash
# Validate all Python files recursively
vallm batch ./my-project --recursive --format toon --output ./project

# JSON output for CI integration
vallm batch ./my-project --recursive --format json

# Errors only, piped to planfile for ticket creation
vallm batch ./my-project --errors-json | planfile ticket import --source vallm
```

The output includes per-file quality scores and categorized issues: import errors, naming violations, missing documentation, structural problems, and pattern deviations.

## Quality criteria

vallm evaluates code across dimensions that complement static analysis:

- **Import hygiene** — are imports resolvable, minimal, and well-organized?
- **Naming quality** — do function and variable names describe their purpose?
- **Documentation** — are docstrings present, accurate, and useful (not just template filler)?
- **Structural coherence** — does the function do one thing, or is it a multi-purpose blob?
- **Convention adherence** — does the code follow patterns established elsewhere in the project?

These criteria are configurable and can be customized per project.

## Ecosystem integration

vallm integrates deeply with the rest of the WronAI toolchain:

**devloop** uses vallm pass rates as quality gates. A pipeline stage runs `vallm batch` and checks whether `vallm_pass_min` threshold is met before proceeding to the next iteration.

**regix** tracks vallm quality scores as one of its regression metrics. If a refactoring causes the LLM quality score to drop from 0.92 to 0.78, regix flags it as a regression at the file level.

**code2llm** provides the structural context that vallm uses for informed validation — rather than evaluating files in isolation, vallm can consider the project's architecture.

**planfile** receives vallm errors as structured tickets via the `--planfile` flag or JSON pipe, with automatic priority assignment based on severity.

## Key lesson: scan only what you own

A critical operational lesson from deploying vallm: running `vallm batch . --recursive` on an entire project root — including `docs/`, `examples/`, `*.yaml`, and `*.md` — inflates the denominator with unsupported file types. The result: a misleading pass rate of 58.3% (56/96 files) when the actual Python source pass rate is 98.2% (56/57 files).

Always configure the scan scope to match your source directories. vallm's `--include` and `--exclude` flags exist precisely for this purpose.

## Output format

vallm produces TOON files (`.toon`) that are consumed by devloop gates and regix snapshots:

```
VALIDATION:
  total: 57
  passed: 52
  failed: 5
  pass_rate: 0.912

ERRORS[5]{file,rule,message}:
  src/parser.py,naming.descriptive,"Function 'proc' has non-descriptive name"
  src/utils.py,import.unused,"Unused import: typing.Optional"
  ...
```

## What's next

Upcoming work includes per-function validation (currently file-level), configurable rule sets, and integration with the planfile MCP server so that LLM assistants can trigger validation and create tickets in a single conversation.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Published on [PyPI](https://pypi.org/project/vallm/).*
