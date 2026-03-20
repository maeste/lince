---
id: LINCE-64
title: Show agent type indicator and unsandboxed warning in dashboard TUI
status: To Do
assignee: []
created_date: '2026-03-20 17:43'
labels:
  - dashboard
  - TUI
  - rendering
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-58
references:
  - lince-dashboard/plugin/src/dashboard.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add visual indicators for agent type in the dashboard. Agent table gets a 3-char type column (CC=Claude, CX=Codex, GM=Gemini, OC=OpenCode). Unsandboxed agents show a bold red "!" warning. Detail panel shows full type name + sandbox status. Colors sourced from AgentTypeConfig.

**Why**: Users managing multiple agent types need to quickly identify each agent's type and sandbox status, especially the security-critical unsandboxed warning.

**Key file**: `plugin/src/dashboard.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Agent table has 3-char type column showing short_label from AgentTypeConfig
- [ ] #2 Unsandboxed agents show red warning indicator (bold red '!' or similar)
- [ ] #3 Detail panel shows 'Type: X (sandboxed)' or 'Type: X (UNSANDBOXED)' with red for unsandboxed
- [ ] #4 Colors sourced from AgentTypeConfig.color
- [ ] #5 Rendering degrades gracefully on narrow terminals (type column can be hidden)
<!-- AC:END -->
