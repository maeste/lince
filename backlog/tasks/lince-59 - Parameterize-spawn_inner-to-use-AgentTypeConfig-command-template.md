---
id: LINCE-59
title: Parameterize spawn_inner() to use AgentTypeConfig command template
status: Done
assignee: []
created_date: '2026-03-20 17:42'
updated_date: '2026-03-24 20:49'
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
Refactor `spawn_inner()` in `agent.rs` to accept `agent_type: &str`, look up the `AgentTypeConfig` from `DashboardConfig.agent_types` HashMap, and build the command from the config's command template with placeholder substitution ({agent_id}, {project_dir}, {profile}).

**Why**: Currently spawn is hardcoded to `claude-sandbox run`. Must be generic for any agent type defined in config.

**Key file**: `plugin/src/agent.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 spawn_inner() signature includes agent_type: &str
- [x] #2 Agent type looked up from DashboardConfig.agent_types HashMap (string key)
- [x] #3 Command built from AgentTypeConfig.command template with placeholder substitution
- [x] #4 LINCE_AGENT_ID env var set for all agent types
- [x] #5 Agents with has_native_hooks=false are wrapped with lince-agent-wrapper
- [x] #6 Claude sandboxed produces identical command to current behavior (regression check)
<!-- AC:END -->
