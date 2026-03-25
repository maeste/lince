---
id: LINCE-58
title: Persist agent type in AgentInfo and state file v2 with backward compat
status: Done
assignee: []
created_date: '2026-03-20 17:42'
updated_date: '2026-03-24 20:47'
labels:
  - dashboard
  - types
  - state-file
  - backward-compat
milestone: m-12
dependencies:
  - LINCE-56
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/state_file.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Persist agent type as a **string key** (not enum) in `AgentInfo` and state file v2 with backward compat. The key references the agent's config entry in `HashMap<String, AgentTypeConfig>`.

**Why**: State files need to record which agent type each instance is, so the dashboard can look up the correct config on reload. String keys keep this simple and forward-compatible — any new agent type added via TOML works without code changes.

**Implementation scope**:
- `AgentInfo` gains `agent_type: String` field (default: `"claude"`)
- State file v2 format includes `agent_type` field
- v1 state files load with implicit `agent_type = "claude"` (backward compat)
- Agent type validated against available configs on load (warn if unknown, don't crash)

**Key files**: `plugin/src/types.rs`, `plugin/src/state_file.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AgentInfo has agent_type: String field (default: "claude")
- [x] #2 State file v2 serializes/deserializes agent_type as string
- [x] #3 v1 state files load with implicit agent_type = "claude" (backward compat)
- [x] #4 Unknown agent_type logs warning but does not crash
- [x] #5 Round-trip: save → reload preserves agent_type correctly
<!-- AC:END -->
