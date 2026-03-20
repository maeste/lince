---
id: LINCE-60
title: Generalize pane reconciliation to support multi-agent title patterns
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
labels:
  - dashboard
  - pane-manager
  - agent
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-58
references:
  - lince-dashboard/plugin/src/agent.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`reconcile_panes()` at agent.rs line ~169 checks `pane.title.contains("claude-sandbox")`. Refactor to use `AgentTypeConfig.pane_title_pattern` for each agent in `Starting` status, preventing cross-matching between different agent types.

**Why**: Different agents produce different pane titles. Without per-type patterns, the dashboard cannot correctly associate panes with agents.

**Key file**: `plugin/src/agent.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Pane matching uses per-agent-type pattern from AgentTypeConfig.pane_title_pattern
- [ ] #2 Claude agents still match 'claude-sandbox'
- [ ] #3 Different agent types starting simultaneously do not cross-match panes
<!-- AC:END -->
