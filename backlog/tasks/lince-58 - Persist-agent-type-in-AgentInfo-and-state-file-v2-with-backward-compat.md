---
id: LINCE-58
title: Persist agent type in AgentInfo and state file v2 with backward compat
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
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
Add `agent_type: String` to `AgentInfo` and `SavedAgentInfo`. Bump state file version to 2. Handle v1 files by defaulting agent_type to "claude".

**Why**: Agent type must survive save/restore cycles. Backward compat ensures existing `.lince-dashboard` files continue working.

**Key files**: `plugin/src/types.rs`, `plugin/src/state_file.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AgentInfo.agent_type field (String) exists
- [ ] #2 SavedAgentInfo.agent_type field with serde default 'claude'
- [ ] #3 STATE_VERSION is 2, parse_loaded_state() handles v1 files (default agent_type='claude')
- [ ] #4 Save→load round-trip preserves agent_type correctly
<!-- AC:END -->
