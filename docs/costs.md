---
title: "costs: Tracking AI API Spend Per Task, Per Model, Per Sprint"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Cost Management, Developer Tools]
tags: [costs, wronai, semcod, llm-costs, api-tracking, pypi, python]
excerpt: "costs provides per-call, per-model cost attribution for LLM API usage in development pipelines. Published on PyPI."
---

# costs: Tracking AI API Spend Per Task, Per Model, Per Sprint

LLM API calls add up. A single complex refactoring task might require multiple model calls — context gathering, code generation, validation, retry — each with different token counts and pricing. Without tracking, the cost of AI-assisted development is a monthly surprise on the API bill.

**costs** provides structured cost tracking for LLM API usage within development pipelines. It attributes costs to specific tasks, models, and time periods, making the cost-quality tradeoff visible.

## Current status

costs is **published on PyPI** and available for installation:

```bash
pip install costs
```

## What it does

costs intercepts or logs LLM API calls and records per-call metadata: model used, input/output token counts, calculated cost (based on provider pricing), task identifier, and timestamp.

This data feeds into proxym dashboards for visualization, into llx for budget-aware model selection, and into sprint reports for cost-per-ticket attribution.

## Why it matters

The WronAI ecosystem's go-to-market learning was that cost-savings pitches fail when the math is marginal. Instead, costs serves an observability purpose: showing *where* money goes rather than promising it will go down. Teams using llx's intelligent routing can see the cost difference between routing everything to a frontier model versus using tiered selection — and decide for themselves whether the tradeoff is worth it.

## Ecosystem role

costs is a utility package consumed by llx (budget constraints for model selection), proxym (cost dashboards), and planfile (cost-per-ticket reporting). It is lightweight by design — a tracking layer, not a billing system.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Published on [PyPI](https://pypi.org/project/costs/).*
