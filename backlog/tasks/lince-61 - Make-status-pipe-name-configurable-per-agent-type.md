---
id: LINCE-61
title: Make status pipe name configurable per agent type
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
labels:
  - dashboard
  - status
  - protocol
milestone: m-12
dependencies:
  - LINCE-56
references:
  - lince-dashboard/plugin/src/main.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently `main.rs` `pipe()` method only listens on `"claude-status"`. Accept messages on both `"claude-status"` (backward compat) and `"lince-status"` (new generic name). Per-agent-type pipe name is configurable via `AgentTypeConfig.status_pipe_name`.

**Why**: Different agent hook scripts may use different pipe names. A single generic name simplifies new agent integration while preserving backward compat for existing Claude hooks.

**Key file**: `plugin/src/main.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Dashboard accepts status messages on both 'claude-status' and 'lince-status' pipe names
- [ ] #2 Per-agent-type pipe name is configurable in AgentTypeConfig
- [ ] #3 Existing Claude hooks continue to work without modification
- [ ] #4 New agents can send status via 'lince-status' pipe
<!-- AC:END -->
