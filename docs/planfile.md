---
title: "planfile: A Universal Ticket Standard for Developer Toolchains"
date: 2026-03-31
author: Tom Sapletta
categories: [AI, Project Management, Developer Tools]
tags: [planfile, wronai, semcod, tickets, yaml, sprint, mcp, python]
excerpt: "planfile is a local, YAML-based ticket standard that any tool — vallm, code2llm, llx, proxym, LLMs, humans — can read, create, and synchronize. For developer tasks, planfile is what package.json is for dependencies."
---

# planfile: A Universal Ticket Standard for Developer Toolchains

When an analysis tool finds 10 high-complexity functions, where do those findings go? Into a terminal log that nobody reads twice. When an LLM fixes 3 files but introduces a regression in one, how does that become a tracked task? It does not — unless someone manually creates a Jira ticket.

**planfile** solves this by providing a local, file-based ticket standard that every tool in the development pipeline can read and write. It is to developer tasks what `.git/` is to version control — a structured local store that integrates with external systems (GitHub Issues, GitLab, Jira) via synchronization.

## Current status

planfile is in active development, currently in Sprint 3. The core design is stabilized: YAML-based ticket format, sprint containers, Python SDK, CLI, and MCP server specification for LLM integration. Sprint 2 delivered the ticket data model and CLI scaffolding. Sprint 3 focuses on importers (code2llm, vallm) and the sync backends.

## The concept

A planfile project stores tickets as YAML files in a `.planfile/` directory:

```
.planfile/
├── config.yaml
├── sprints/
│   ├── current.yaml     # active sprint
│   ├── backlog.yaml     # backlog
│   └── sprint-001.yaml  # archived sprints
├── sync/
│   ├── github.state.yaml
│   └── jira.state.yaml
└── hooks/
    └── on-ticket-create.sh
```

Each ticket is a structured YAML object with an ID, title, status, priority, sprint assignment, source tool reference, description, acceptance criteria, and LLM execution hints.

## Multi-tool integration

The key value proposition: every tool in the WronAI ecosystem can create, read, and update planfile tickets through a shared SDK:

**code2llm** converts evolution.toon refactoring priorities into planfile tickets with `--planfile` flag. Impact-based priority assignment maps high-CC functions to critical priority.

**vallm** pipes validation errors into tickets with `vallm batch . --errors-json | planfile ticket import --source vallm`. Each error becomes a trackable task with the original file, rule, and context attached.

**llx** reads tickets, executes them via LLM, and updates status. A ticket executor selects the appropriate model based on the ticket's complexity hints and budget constraints.

**proxym** displays sprint dashboards showing ticket counts, gate status, and progress bars — all reading from the same `.planfile/` directory.

## MCP server

planfile specifies an MCP (Model Context Protocol) server that exposes tickets as resources and operations as tools. This means LLM assistants (Claude, GPT) can directly interact with the ticket system:

- Read current sprint status as context
- Create tickets from diagnostic results
- Update ticket status after completing tasks
- Trigger GitHub/GitLab synchronization

## What's next

Sprint 3 deliverables: importers for code2llm and vallm output, sync backend for GitHub Issues (bidirectional), and the first version of the MCP server specification. The vision is a fully connected loop where tools create tickets, LLMs execute them, and humans review on dashboards.

---

*Part of the [WronAI ecosystem](https://github.com/semcod). Source: [github.com/semcod/planfile](https://github.com/semcod/planfile).*
