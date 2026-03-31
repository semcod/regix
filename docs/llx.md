---
title: "llx: Intelligent LLM Router for Development Tasks"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, LLM, Developer Tools]
tags: [llx, wronai, semcod, llm-routing, model-selection, python]
excerpt: "llx routes development tasks to the right LLM model based on complexity, cost, and quality constraints. Not every fix needs GPT-4 — and not every refactoring should be entrusted to the cheapest model."
---

# llx: Intelligent LLM Router for Development Tasks

Using the most capable LLM for every development task is expensive and unnecessary. Reformatting imports does not need a frontier model. But splitting a CC=65 function into coherent sub-functions with proper interfaces does. The challenge is making this routing decision automatically, per-task, based on measurable criteria.

**llx** is an intelligent LLM router that selects models per-task based on complexity, cost constraints, and quality requirements. It sits between the pipeline orchestrator (devloop) and the LLM API, making cost-quality tradeoffs explicit and automatic.

## Current status

llx is in Sprint 4 development. The core routing logic and model selection strategies are being built. The planned integration with planfile will enable ticket-aware execution: llx reads a planfile ticket, selects the appropriate model based on the ticket's complexity hints, executes the task, validates with vallm, and updates the ticket status.

## How it works

llx classifies tasks into tiers and routes accordingly:

- **Simple** tasks (formatting, import cleanup, docstring addition) route to fast, cheap models
- **Balanced** tasks (function extraction, renaming, test generation) use mid-tier models
- **Premium** tasks (complex refactoring, architecture changes, multi-file restructuring) use frontier models

The classification is based on signals from code2llm (cyclomatic complexity, function length, dependency count) and planfile ticket metadata (effort estimates, file count, acceptance criteria complexity).

## Planned features

**Ticket execution.** `llx plan apply --ticket PLF-051 ./my-project` reads a planfile ticket, builds context, selects a model, generates a fix, validates with vallm, and updates the ticket — all in one command.

**Cost budgets.** Per-sprint cost limits: "spend at most $50 on this sprint's tickets." llx optimizes model selection to maximize quality within the budget.

**Fallback chains.** If the selected model fails (rate limit, timeout, quality gate failure), llx falls back to the next tier automatically.

**Validation loop.** After generating a fix, llx runs vallm to validate. If validation fails, it retries with more context or a higher-tier model before marking the task as blocked.

## Ecosystem role

llx is the execution engine. While devloop orchestrates the pipeline and decides *when* to fix, llx decides *how* — which model to use, what context to provide, and how to validate the result. It completes the loop from "metric violation detected" to "fix applied and validated."

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Source: [github.com/semcod/llx](https://github.com/semcod/llx).*
