---
title: "proxym: The Dashboard Layer for AI-Assisted Development"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Dashboard, Developer Tools]
tags: [proxym, wronai, semcod, dashboard, quality-gates, python]
excerpt: "proxym provides the human interface for the WronAI pipeline — a web dashboard showing quality gate status, sprint progress, regression trends, and pipeline execution state."
---

# proxym: The Dashboard Layer for AI-Assisted Development

Automated pipelines produce data. Lots of it — quality scores, regression reports, gate results, cost breakdowns, sprint status. Without a dashboard, this data lives in JSON files and terminal logs. proxym gives it a human interface.

**proxym** is the web dashboard layer for the WronAI ecosystem. It reads data from code2llm analysis files, vallm reports, regix regression histories, devloop pipeline state, and planfile sprint tickets — then renders it as an interactive dashboard.

## Current status

proxym is in Sprint 2 development. The current focus is a major refactoring of the provider layer: reducing `providers/__init__.py` from 561 lines to ~210, dropping `_generate_cli_command` from CC=61 to ≤15, and integrating planfile as the primary ticket data source.

Key Sprint 2 targets:

- Provider layer refactoring (net -760 lines)
- planfile ticket importer and sprint tracker
- Quality gate dashboard widget
- Pipeline execution status display

## Planned capabilities

**Quality gate overview** — at-a-glance pass/fail status for all configured gates: cc_max, vallm_pass_min, coverage_min, regression_errors_max. Color-coded, with drill-down to individual violations.

**Sprint dashboard** — imported from planfile, showing ticket counts by status (open, in_progress, done, blocked), progress bars, and source attribution (which tool created each ticket).

**Regression timeline** — sourced from regix history reports, showing metric trends across commits with degradation alerts.

**Cost tracking** — sourced from the costs package, showing per-model, per-task API cost attribution.

**Chat interface** — proxym includes an LLM chat interface for human-assisted operations: reviewing pipeline results, asking for explanations, and triggering manual actions.

## Architecture

proxym follows a provider-consumer architecture. Providers read data from various sources (file-based TOON/JSON artifacts, planfile SDK, costs database). The dashboard layer renders this data as web components. The chat layer enables conversational interaction with the pipeline state.

## Ecosystem role

proxym is the observability layer. While the other tools in the ecosystem run headless (CLI or API), proxym is where humans look. It closes the feedback loop by making automated pipeline activity visible, actionable, and reviewable.

The end-to-end flow: planfile generates strategy → llx executes (selecting models per-task) → proxym tracks progress → the dashboard shows which gates pass, what the cost is, and where regressions appeared.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Source: [github.com/semcod/proxym](https://github.com/semcod/proxym).*
