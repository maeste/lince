---
id: LINCE-59
title: Parameterize spawn_inner() to use AgentTypeConfig command template
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
labels:
  - dashboard
  - agent
  - spawn
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
Refactor `spawn_inner()` in `agent.rs` to accept `agent_type: &str`, look up the `AgentTypeConfig` from `DashboardConfig`, and build the command from the config's command template with placeholder substitution ({agent_id}, {project_dir}, {profile}). `spawn_agent_custom()` gains an `agent_type` parameter.

**Why**: Currently spawn is hardcoded to `claude-sandbox run`. Must be generic for any agent type.

**Key file**: `plugin/src/agent.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 spawn_inner() signature includes agent_type: &str
- [ ] #2 Command built from AgentTypeConfig.command template with placeholder substitution
- [ ] #3 LINCE_AGENT_ID env var set for all agent types
- [ ] #4 Claude sandboxed produces identical command to current behavior (regression check)
- [ ] #5 Claude unsandboxed produces 'env LINCE_AGENT_ID=... claude'
<!-- AC:END -->
