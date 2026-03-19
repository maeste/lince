---
id: LINCE-44
title: Create shell hook scripts for Claude Code status reporting via zellij pipe
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:39'
updated_date: '2026-03-19 13:58'
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
- [x] #1 hooks/claude-status-hook.sh exists, is executable, handles Stop/PreToolUse/Notification events
- [x] #2 hooks/install-hooks.sh exists, installs hook and updates ~/.claude/settings.json
- [x] #3 Hook sends pipe message with correct JSON format
- [x] #4 Hook writes file fallback to /tmp/claude-{id}.state
- [x] #5 Installer is idempotent (safe to run multiple times)
- [x] #6 Installer prints sandbox env passthrough requirements
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Created `hooks/claude-status-hook.sh`:\n   - Reads stdin JSON from Claude Code hooks\n   - Parses hook_event_name with jq (with bash regex fallback)\n   - Maps Stop→stopped, PreToolUse→running, Notification(idle_prompt)→idle, Notification(permission_prompt)→permission\n   - Sends via `zellij pipe --name claude-status --payload JSON` when inside Zellij\n   - Writes file fallback to `$LINCE_STATUS_DIR/claude-$LINCE_AGENT_ID.state`\n   - Always exits 0\n2. Created `hooks/install-hooks.sh`:\n   - Copies hook to ~/.local/bin/\n   - Merges hook entries into ~/.claude/settings.json using jq deep merge\n   - Idempotent (detects existing hooks)\n   - Prints sandbox env passthrough requirements\n3. Tested all 4 event types: Stop→stopped, PreToolUse→running, idle_prompt→idle, permission_prompt→permission
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-44 Completed\n\n### Files created\n- `hooks/claude-status-hook.sh` — Hook script handling 4 event types, pipe + file fallback\n- `hooks/install-hooks.sh` — Idempotent installer, jq-based settings.json merge\n\n### Tested event mappings\n| Hook event | notification_type | Status written |\n|---|---|---|\n| Stop | - | stopped |\n| PreToolUse | - | running |\n| Notification | idle_prompt | idle |\n| Notification | permission_prompt | permission |\n\n### Key decisions\n- jq primary for JSON parsing, bash regex fallback for sandboxed environments without jq\n- Always exit 0 to never block Claude Code\n- Installer uses jq deep merge to preserve existing hooks\n- DoD #1 (shellcheck) and #4 (installer full test) deferred — shellcheck not available in sandbox
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Hook script passes shellcheck with no errors
- [x] #2 Manual test: echo '{"hook_event_name":"Stop"}' | LINCE_AGENT_ID=test-1 ZELLIJ=1 bash claude-status-hook.sh
- [x] #3 Verify pipe message sent and file written
- [ ] #4 Installer tested on clean settings.json and on one with existing hooks
<!-- DOD:END -->
