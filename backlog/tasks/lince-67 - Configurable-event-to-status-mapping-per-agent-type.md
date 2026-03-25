---
id: LINCE-67
title: Configurable event-to-status mapping per agent type
status: Done
assignee: []
created_date: '2026-03-20 17:43'
updated_date: '2026-03-25 07:04'
labels:
  - dashboard
  - status
  - extensibility
milestone: m-12
dependencies:
  - LINCE-56
references:
  - lince-dashboard/plugin/src/types.rs
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add optional `event_map: HashMap<String, String>` to `AgentTypeConfig`. `StatusMessage::to_agent_status()` consults this map when available, falling back to current defaults. Enables custom agents to define their own event vocabulary.

**Why**: Different agents may emit different event strings. This extensibility point allows adding new agents without code changes.

**Key file**: `plugin/src/types.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AgentTypeConfig has optional event_map field (HashMap<String, String>)
- [x] #2 to_agent_status() uses event_map when available, falls back to current defaults
- [x] #3 Default Claude mappings preserved when no custom map set
- [x] #4 Custom agent can map arbitrary event strings to AgentStatus variants
<!-- AC:END -->
