---
id: LINCE-44
title: Create shell hook scripts for Claude Code status reporting via zellij pipe
status: To Do
assignee: []
created_date: '2026-03-19 10:39'
labels:
  - dashboard
  - hooks
  - shell
milestone: m-10
dependencies:
  - LINCE-42
references:
  - sandbox/claude-sandbox (env passthrough in config)
  - Claude Code hooks documentation
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Shell scripts that Claude Code invokes on lifecycle events to report status to the dashboard plugin via Zellij pipe (primary) with file fallback. Plus an installer that configures the hooks in Claude Code settings.

## Implementation Plan

1. Create `lince-dashboard/hooks/claude-status-hook.sh`:
   - Read hook event from stdin JSON (Claude Code pipes JSON to hook stdin)
   - Parse `hook_event_name` field using `jq` or bash string parsing
   - Read `LINCE_AGENT_ID` env var (set by dashboard at agent spawn, passed through sandbox env)
   - Map events: `Stop`→stopped, `PreToolUse`→running, `Notification` with `idle_prompt`→idle, `permission_prompt`→permission
   - Build JSON payload: `{"agent_id":"...","event":"...","timestamp":"..."}`
   - Send via `zellij pipe --name "claude-status" --payload "$PAYLOAD"` if `$ZELLIJ` is set
   - Write to `${LINCE_STATUS_DIR:-/tmp}/claude-${LINCE_AGENT_ID}.state` as fallback
   - Exit 0 always (hooks must not block Claude Code)
2. Create `lince-dashboard/hooks/install-hooks.sh`:
   - Copy hook script to `~/.local/bin/claude-status-hook.sh`
   - Read `~/.claude/settings.json` (create if absent)
   - Add hooks for events: `Stop`, `PreToolUse`, `Notification`
   - Merge with existing hooks (don't overwrite)
   - Verify `jq` available
   - Print sandbox requirements: `ZELLIJ`, `ZELLIJ_SESSION_NAME`, `LINCE_AGENT_ID` must be in sandbox env passthrough
3. Document: sandbox config needs `env.passthrough = ["ZELLIJ", "ZELLIJ_SESSION_NAME", "LINCE_AGENT_ID"]`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 hooks/claude-status-hook.sh exists, is executable, handles Stop/PreToolUse/Notification events
- [ ] #2 hooks/install-hooks.sh exists, installs hook and updates ~/.claude/settings.json
- [ ] #3 Hook sends pipe message with correct JSON format
- [ ] #4 Hook writes file fallback to /tmp/claude-{id}.state
- [ ] #5 Installer is idempotent (safe to run multiple times)
- [ ] #6 Installer prints sandbox env passthrough requirements
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Hook script passes shellcheck with no errors
- [ ] #2 Manual test: echo '{"hook_event_name":"Stop"}' | LINCE_AGENT_ID=test-1 ZELLIJ=1 bash claude-status-hook.sh
- [ ] #3 Verify pipe message sent and file written
- [ ] #4 Installer tested on clean settings.json and on one with existing hooks
<!-- DOD:END -->
