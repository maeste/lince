---
id: LINCE-65
title: Create generic agent wrapper script for lifecycle status reporting
status: Done
assignee: []
created_date: '2026-03-20 17:43'
updated_date: '2026-03-25 06:57'
labels:
  - dashboard
  - hooks
  - scripts
milestone: m-12
dependencies:
  - LINCE-61
references:
  - lince-dashboard/hooks/claude-status-hook.sh
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Claude Code has native hooks that report status. Other agents do not. Create a `lince-agent-wrapper` shell script that wraps any agent command, sends start/stop lifecycle events via `zellij pipe`.

**Why**: Without this, non-Claude agents would have no status reporting to the dashboard. The wrapper provides baseline Started/Stopped lifecycle for any agent.

**Implementation**: Shell script that accepts agent command + agent ID + pipe name. Sends start JSON on startup and stopped JSON on exit (via trap). Agents with `has_native_hooks: true` in config bypass this wrapper (spawn_inner checks the config field).

**Key file**: `lince-dashboard/hooks/lince-agent-wrapper` (new)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 lince-agent-wrapper script exists and is executable
- [x] #2 Script accepts: agent command, agent ID, pipe name as arguments
- [x] #3 Sends start event JSON via zellij pipe on startup
- [x] #4 Sends stopped event JSON via zellij pipe on exit (via trap)
- [x] #5 Agents with has_native_hooks=true in config are NOT wrapped (checked by spawn_inner)
- [x] #6 Script is referenced in command templates for non-native-hook agent types
<!-- AC:END -->
