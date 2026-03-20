---
id: LINCE-65
title: Create generic agent wrapper script for lifecycle status reporting
status: To Do
assignee: []
created_date: '2026-03-20 17:43'
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
Claude Code has native hooks that report status. Other agents (Codex, Gemini, OpenCode) do not. Create a `lince-agent-wrapper` shell script that wraps any agent command, sends start/stop lifecycle events via `zellij pipe --name "lince-status"`.

**Why**: Without this, non-Claude agents would have no status reporting to the dashboard. The wrapper provides baseline Started/Stopped lifecycle for any agent.

**Implementation**: Shell script that accepts agent command + agent ID + pipe name. Sends `{"agent_id":"...","event":"start"}` on startup and `{"agent_id":"...","event":"stopped"}` on exit (via trap). Claude agents bypass this wrapper (use their own hooks).

**Key file**: `lince-dashboard/hooks/lince-agent-wrapper` (new)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 lince-agent-wrapper script exists and is executable
- [ ] #2 Script accepts: agent command, agent ID, pipe name as arguments
- [ ] #3 Sends start event JSON via zellij pipe on startup
- [ ] #4 Sends stopped event JSON via zellij pipe on exit (via trap)
- [ ] #5 Claude agents are NOT wrapped (use native hooks instead)
- [ ] #6 Script is referenced in command templates for non-Claude agent types
<!-- AC:END -->
