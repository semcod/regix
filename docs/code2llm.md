---
title: "code2llm: The Static Analysis Engine That Speaks LLM"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Developer Tools, Static Analysis]
tags: [code2llm, wronai, semcod, toon, static-analysis, python]
excerpt: "code2llm scans your codebase and produces structured context files — TOON format — that LLMs, dashboards, and quality pipelines can consume directly. It bridges the gap between raw source code and actionable intelligence."
---

# code2llm: The Static Analysis Engine That Speaks LLM

Static analysis tools have existed for decades. They parse code, count complexity, flag style violations, and produce reports. But those reports are designed for humans reading terminals — not for LLMs processing context, not for dashboards rendering status, and not for automated pipelines making decisions.

**code2llm** bridges this gap. It scans a codebase and produces structured output in a format called TOON — a machine-readable plain-text format that is simultaneously greppable by humans and parseable by downstream tools.

## What it produces

A single `code2llm` run generates multiple output files, each serving a different purpose:

**analysis.toon** contains a health assessment of the project: cyclomatic complexity per function, refactoring candidates, risk areas, and aggregate statistics. This is the file you grep when you want to know "what is the worst function in this codebase?"

**evolution.toon** is a prioritized refactoring queue. It ranks technical debt items by impact (complexity × usage frequency) and suggests a next-action order. This feeds directly into planfile tickets and devloop pipeline stages.

**map.toon** provides the structural overview: modules, imports, public API signatures, and dependency relationships. Think of it as the architecture diagram in text form.

**context.md** is a ready-to-paste narrative for AI assistants — a structured summary of the project's architecture, entry points, design patterns, and data flows. Copy this into an LLM conversation to give it deep project understanding.

**Visualization files** (`.mmd`, `.png`) render control flow and call graphs as Mermaid diagrams, with complexity color-coding.

## Current status

code2llm is the most mature package in the WronAI ecosystem. It is published and actively developed, with a comprehensive exporter system covering multiple output formats: TOON, JSON, Markdown context, Mermaid flow diagrams, and evolution reports.

The core analysis engine handles Python with multi-language support in progress. It detects functions, classes, imports, call graphs, and computes cyclomatic complexity at symbol level.

Recent development has focused on the planfile integration — a `--planfile` flag that automatically converts evolution.toon items into structured tickets, ready for sprint planning.

## Architecture

code2llm follows a parser-exporter architecture:

The **core** contains language-specific parsers that extract structural information from source files. The Python parser uses the `ast` module for reliable parsing; other languages use tree-sitter bindings.

The **exporters** transform parsed data into output formats. Each exporter is a self-contained module: `analysis_exporter.py`, `evolution_exporter.py`, `flow_exporter.py`, `context_exporter.py`, and so on.

The **CLI** orchestrates the pipeline: parse → analyse → export, with flags for output format selection, file filtering, and integration options.

## Usage

```bash
# Full analysis with all outputs
code2llm ./my-project -f toon

# Just the evolution (refactoring priority) report
code2llm ./my-project -f evolution

# LLM-ready context for pasting into a conversation
code2llm ./my-project -f context

# Auto-create planfile tickets from diagnostics
code2llm ./my-project -f evolution --planfile --planfile-sprint backlog
```

## The TOON format

TOON is a deliberate design choice. It sits between JSON (structured but hard to scan visually) and plain text (human-friendly but hard to parse). A TOON file uses section headers, tagged lists, and consistent formatting that makes it simultaneously greppable and parseable:

```
HEALTH:
  status: yellow
  issues:
    CC_HIGH: _extract_declarations CC=65 (threshold: 15)
    CC_HIGH: _parse_imports CC=31 (threshold: 15)

NEXT[3]{action,target,impact,effort}:
  SPLIT,_extract_declarations,3250,~2h
  SPLIT,_parse_imports,1550,~1h
  EXTRACT,_build_type_map,890,~30m
```

This format is consumed by vallm (for quality scoring context), devloop (for gate checking), regix (for regression baselines), and planfile (for ticket generation).

## Ecosystem role

code2llm is the entry point of the analysis pipeline. Everything downstream depends on the structural data it produces. When vallm validates code quality, it reads code2llm's analysis. When devloop checks gates, it reads code2llm's metrics. When planfile generates tickets, it reads code2llm's evolution priorities.

## What's next

The near-term roadmap includes expanding multi-language support via tree-sitter, adding incremental analysis (only re-scan changed files), and deepening the planfile integration for automatic ticket lifecycle management.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). See also: [vallm](/vallm), [regix](/regix), [devloop](/devloop).*
