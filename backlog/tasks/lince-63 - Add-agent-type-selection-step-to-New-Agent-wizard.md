---
id: LINCE-63
title: Add agent type selection step to New Agent wizard
status: Done
assignee: []
created_date: '2026-03-20 17:42'
updated_date: '2026-03-25 06:56'
labels:
  - dashboard
  - wizard
  - UX
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-59
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/dashboard.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add agent type selection step to the New Agent wizard. The wizard lists all available agent configs — both built-in presets from `agents-defaults.toml` and user-defined entries from `config.toml`.

**Why**: Users need to choose which agent to spawn. Listing config keys (not enum variants) means user-defined agents appear automatically with no code changes.

**Implementation scope**:
- Wizard step reads available keys from `DashboardConfig.agent_types`
- Each entry shows `display_name` and `short_label` from config
- Selected agent type stored in spawn request and passed to `spawn_inner()`
- Default selection: first entry or `"claude"` if available

**Key file**: `plugin/src/ui.rs` or wizard module
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Wizard lists all agent types from config (built-in + user-defined)
- [x] #2 Each entry shows display_name from AgentTypeConfig
- [x] #3 Selected agent type passed to spawn_inner()
- [x] #4 User-defined agents in TOML appear in wizard without code changes
- [x] #5 Default selection is 'claude' if available
<!-- AC:END -->
