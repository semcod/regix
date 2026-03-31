---
title: "redup: Detecting Code Duplication Across Your Codebase"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Code Quality, Refactoring]
tags: [redup, wronai, semcod, duplication, dry, python]
excerpt: "redup identifies redundant and duplicated code across a codebase, surfacing consolidation opportunities that other analysis tools miss."
---

# redup: Detecting Code Duplication Across Your Codebase

Copy-paste is the fastest way to write code and the slowest way to maintain it. Duplicated logic means duplicated bugs, duplicated fixes, and divergent implementations that were once identical. Standard linters flag some duplication, but usually at the level of identical lines rather than semantic similarity.

**redup** is a duplication analyzer designed to find not just identical code blocks but structurally similar patterns — functions that do the same thing with different variable names, classes that implement the same interface with minor variations, and modules that could be consolidated.

## Current status

redup is in early development. The core concept is defined: scan a codebase, build a structural fingerprint per function/class, cluster similar fingerprints, and report consolidation candidates with estimated effort savings.

## Planned capabilities

- **Exact duplication** — identical or near-identical code blocks across files
- **Structural similarity** — functions with the same control flow but different names and variables
- **Cross-module patterns** — repeated patterns that suggest a missing abstraction
- **Impact estimation** — how many lines could be saved by consolidating each duplicate group

## Ecosystem role

redup complements code2llm's complexity analysis. Where code2llm identifies high-CC functions that need splitting, redup identifies duplicate functions that need merging. Both produce inputs for planfile tickets and devloop pipeline stages.

The combination of code2llm (what to split), redup (what to merge), and regix (did the refactoring make things worse) creates a comprehensive refactoring feedback loop.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Source: [github.com/semcod/redup](https://github.com/semcod/redup).*
