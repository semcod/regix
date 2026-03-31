---
title: "code2docs: Generating Documentation From Code Analysis Artifacts"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Documentation, Developer Tools]
tags: [code2docs, wronai, semcod, documentation, python]
excerpt: "code2docs transforms the structural analysis produced by code2llm into human-readable documentation — API references, architecture guides, and module overviews — kept in sync with the actual codebase."
---

# code2docs: Generating Documentation From Code Analysis Artifacts

Documentation goes stale. The API reference written six months ago no longer matches the code. The architecture diagram shows modules that were renamed. The getting-started guide imports functions that were moved. Keeping documentation synchronized with a changing codebase is a maintenance burden that most teams eventually give up on.

**code2docs** approaches this differently: instead of writing documentation manually and hoping it stays current, it generates documentation from the structural analysis artifacts that code2llm produces on every run.

## Current status

code2docs is in early development. The concept builds on code2llm's existing output formats — TOON analysis files, context.md narratives, and Mermaid diagrams — to produce structured documentation that updates automatically whenever the analysis runs.

## Planned capabilities

- **API reference generation** — from code2llm's map.toon (signatures, imports, public interfaces)
- **Architecture documentation** — from code2llm's flow.toon (data pipelines, module relationships)
- **Module overviews** — from code2llm's analysis.toon (health status, complexity metrics, refactoring priorities)
- **Changelog generation** — from regix comparison reports (what changed between versions)

## Ecosystem role

code2docs consumes outputs from code2llm and regix to produce documentation artifacts. It is the read-side complement to the analysis pipeline: code2llm analyses the code, code2docs explains it.

The generated documentation can be published as Markdown files (for GitHub/GitLab wikis), HTML pages (for static site generators), or WordPress-ready posts — closing the gap between code analysis and stakeholder communication.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Source: [github.com/semcod/code2docs](https://github.com/semcod/code2docs).*
