---
title: "devloop: Declarative Quality Pipelines That Run Until Your Code Passes"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, DevOps, Code Quality]
tags: [devloop, wronai, semcod, pipeline, quality-gates, yaml, python]
excerpt: "devloop runs YAML-defined quality pipelines in an iterative loop — analyse, validate, check gates, fix, repeat — until all thresholds are met or stagnation is detected."
---

# devloop: Declarative Quality Pipelines That Run Until Your Code Passes

Most CI pipelines are linear: build, test, report. If a quality gate fails, the pipeline fails, and a human investigates. But with LLM-assisted development, there is a new option: when a gate fails, feed the diagnostics back to an LLM, apply the fix, re-validate, and check again. Automatically. In a loop.

**devloop** makes this loop declarative. You define your quality pipeline in YAML — stages, tools, thresholds — and devloop runs it iteratively until all gates pass or stagnation is detected.

## Current status

devloop v0.1.0 is built: 557 lines across 5 files, with 10 passing tests. It provides a Typer CLI with four commands (`init`, `run`, `gates`, `status`) and a YAML-driven pipeline engine.

## How it works

A devloop pipeline is a YAML file defining stages and quality gates:

```yaml
pipeline:
  max_iterations: 5

  metrics:
    cc_max: 15
    vallm_pass_min: 0.90
    coverage_min: 80

  stages:
    - name: analyze
      tool: code2llm
      when: first_iteration

    - name: validate
      run: vallm batch . --recursive --format toon --output ./project
      when: always

    - name: test
      tool: pytest
      optional: true

    - name: fix
      run: llx fix . --apply --errors .devloop/errors.json
      when: metrics_fail
      timeout: 1800

  gates:
    cc_max: 15
    vallm_pass_min: 0.90
```

devloop reads the pipeline definition, executes each stage in order, checks quality gates against the configured thresholds, and — if gates fail — re-runs the fix stage and checks again. The loop continues until all gates pass or `max_iterations` is reached.

## Key concepts

**Quality gates** use a naming convention (`cc_max`, `coverage_min`, `vallm_pass_min`) that maps directly to metrics produced by code2llm and vallm. The suffix `_max` means the value must be ≤ threshold; `_min` means ≥ threshold.

**Stage conditions** (`when: first_iteration`, `when: always`, `when: metrics_fail`) control which stages run on which iteration. Analysis only needs to run once; validation runs every time; fixes only run when gates fail.

**Stagnation detection** prevents infinite loops. If two consecutive iterations produce identical gate values, devloop exits early — continuing would waste compute without progress.

**TOON file consumption.** devloop reads `.toon` files and JSON artifacts produced by code2llm and vallm to evaluate gates. This is the interoperability mechanism: each tool writes its output in a standard format, and devloop reads it.

## Design motivation

devloop was created as a separate focused package rather than extending algitex (which had grown into a large, complex codebase with quality issues of its own). This follows the ecosystem's core principle: one concern per package, narrow interfaces, and interoperability through file-based artifacts.

## Ecosystem role

devloop is the orchestrator. It calls code2llm, vallm, regix, and llx as pipeline stages. It consumes their outputs to evaluate gates. It is the tool that turns a collection of standalone analysis tools into an automated quality improvement loop.

## What's next

Planned work includes deeper regix integration (regression checking as a gate), parallel stage execution, and a proxym dashboard integration for real-time pipeline monitoring.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Source: [github.com/semcod/devloop](https://github.com/semcod/devloop).*
