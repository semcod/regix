---
title: "WronAI Ecosystem: From AI Shepherd to Software Architect"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Developer Tools, Open Source]
tags: [wronai, semcod, llm, devtools, python, code-quality]
excerpt: "An interconnected suite of Python tools that transforms how developers work with AI — shifting from watching AI run in a shell to designing pipelines, defining LLM-integrated SDLC strategies, and intervening only at edge cases."
---

# WronAI Ecosystem: From AI Shepherd to Software Architect

Most developers using AI-assisted coding tools today operate as **AI shepherds** — they watch the AI generate code in a terminal, manually review every output, copy-paste results, and hope nothing regresses. The feedback loop is slow, unstructured, and invisible to the rest of the team.

The **WronAI ecosystem** (semcod/wronai) is a collection of interconnected Python packages designed to change this. The goal: let developers become **architects** who design quality pipelines, set measurable gates, and let automated tools handle the iteration loop. This philosophy is called *progresywna algorytmizacja* — progressive algorithmization.

## The problem

When teams adopt LLM-assisted development, several gaps appear:

- **No measurement layer.** AI generates code, but nobody tracks whether it introduced technical debt. Static analysis runs *after* the fact, disconnected from the generation step.
- **No quality feedback loop.** A linter might flag issues, but there is no structured way to feed those issues back into the LLM for correction and re-validate the output.
- **No regression tracking.** Refactoring over multiple iterations improves some metrics and silently worsens others. Without delta tracking, these regressions stay invisible until a gate breaks.
- **No cost visibility.** LLM API calls accumulate cost, but there is no per-task, per-model cost attribution linked to the development pipeline.

## The ecosystem

Each package in WronAI addresses one concern. They are designed to work standalone but interoperate through shared file formats (TOON, YAML, JSON artifacts):

| Package | Role | Status |
|---|---|---|
| **code2llm** | Static analysis engine — parses codebases and generates LLM-ready context files (TOON format) | Published, active development |
| **vallm** | LLM code validator — batch-validates code against quality rules using LLMs | Published on PyPI |
| **regix** | Regression detection — compares metrics across git versions at symbol granularity | v0.1.0, 49 tests passing |
| **devloop** | Declarative pipeline runner — YAML-driven quality gate loops | v0.1.0, 557 lines, 10 tests |
| **planfile** | Universal ticket standard — local YAML-based task management consumed by all tools | Sprint 3, design stabilized |
| **llx** | Intelligent LLM router — selects models per-task based on complexity and cost constraints | Sprint 4 |
| **proxym** | Dashboard layer — web UI for pipeline status, quality gates, and ticket tracking | Sprint 2 |
| **costs** | AI cost tracker — per-call, per-model cost attribution | Published on PyPI |
| **algitex** | Git history analysis — surfaces development patterns and deficits | Existing, quality review |
| **redup** | Duplication analyzer — detects redundant code across a codebase | Early stage |
| **code2docs** | Documentation generator — produces docs from code analysis artifacts | Early stage |

## How they connect

The interoperability pattern is straightforward: each tool produces artifacts (TOON files, JSON, YAML) that downstream tools can consume.

A typical automated flow:

1. **code2llm** scans the codebase and produces `analysis.toon`, `evolution.toon`, and `map.toon` files with structural data, complexity metrics, and refactoring priorities.
2. **vallm** validates the code against quality rules and outputs per-file pass/fail scores.
3. **devloop** runs a YAML-defined pipeline that checks quality gates (CC thresholds, vallm pass rates, coverage minimums). If gates fail, it triggers a fix stage and re-validates in a loop.
4. **regix** compares the before/after snapshots to detect regressions at function-level granularity — ensuring that fixes in one area did not introduce problems elsewhere.
5. **planfile** captures all diagnostics as structured tickets, prioritized and sprint-ready.
6. **llx** executes fix tasks by routing to the appropriate LLM model based on task complexity and budget.
7. **costs** tracks every API call for budget control.
8. **proxym** displays the entire pipeline state on a dashboard.

## Design principles

Several principles emerged from operational experience building and running these tools:

**Narrow packages over god modules.** The algitex codebase grew large and accumulated quality issues. This became the cautionary example that drove the one-concern-per-package architecture. devloop was built as a separate focused tool rather than extending algitex further.

**Measure what you own.** Running analysis tools on documentation, examples, and config files inflates denominators and produces misleading pass rates. Every tool in the ecosystem is configured to scan only the files it can meaningfully analyse.

**Symbol-level reporting.** File-level averages hide outliers. A file with average CC of 6.4 may contain a function with CC of 26. All tools report at the smallest attributable unit — function or class — so that fixes are targeted.

**Regression ≠ violation.** A function with CC=18 that had CC=18 last month is technical debt, not a regression from this PR. Mixing these concepts creates alert fatigue. Regix separates delta-based regression detection from absolute threshold checking.

**Cost-quality tradeoff is explicit.** Using a top-tier model for every fix task is wasteful. llx routes simple formatting tasks to cheaper models and reserves expensive models for complex refactoring. The costs package makes this tradeoff visible.

## Current focus

The ecosystem is actively developed with a focus on the Polish market, particularly smaller IT teams (up to ~15 people) in the Trójmiasto area. The go-to-market strategy emphasizes quality observability — the gap between AI-generated code and the absence of structured measurement for AI-introduced technical debt.

Community engagement happens through AI Tinkerers Poland, Infoshare, DevAI by DSS, the SpeakLeash Discord, and AI Hub Polska.

## Getting started

Each package is installable via pip:

```bash
pip install vallm
pip install costs
pip install regix  # coming soon
```

Source code: [github.com/semcod](https://github.com/semcod)

---

*This article is part of a series covering each project in the WronAI ecosystem. See the individual articles for detailed status, architecture, and usage guides.*
