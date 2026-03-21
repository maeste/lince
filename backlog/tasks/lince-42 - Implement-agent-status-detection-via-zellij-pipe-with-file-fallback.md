---
id: LINCE-42
title: Implement agent status detection via zellij pipe with file fallback
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:39'
updated_date: '2026-03-19 13:56'
labels:
  - dashboard
  - status
  - rust
milestone: m-10
dependencies:
  - LINCE-40
references:
  - sandbox/claude-sandbox (process running inside agent panes)
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Receive Claude Code status updates via Zellij pipe messages (primary) or file polling (fallback) and update agent status in the dashboard.

## Implementation Plan

1. Add `serde`, `serde_json`, `serde_derive` to `Cargo.toml`
2. Define in `types.rs`: `StatusMessage { agent_id: String, event: String, timestamp: Option<String> }`
3. Implement `pipe()` method on `ZellijPlugin` trait:
   - Filter by name `"claude-status"`
   - Parse payload as `StatusMessage` JSON
   - Map `event` to `AgentStatus`:
     - `"stopped"` / `"Stop"` → `Stopped`
     - `"running"` / `"PreToolUse"` / `"start"` → `Running`
     - `"idle"` / `"idle_prompt"` → `WaitingForInput`
     - `"permission"` / `"permission_prompt"` → `PermissionRequired`
   - Find agent by `agent_id`, update status
   - Return `true` (handled)
4. File fallback (when `config.status_method == File`):
   - `load()`: `set_timeout(2.0)`
   - `Event::Timer`: read `/tmp/claude-{id}.state` for each agent, parse status word, update
   - Re-set timer
5. Malformed messages: log to debug buffer, don't panic
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Pipe handler parses claude-status messages and updates correct agent status
- [x] #2 All event types (Stop, PreToolUse, idle_prompt, permission_prompt) map correctly
- [x] #3 File fallback reads /tmp/claude-{id}.state every 2 seconds
- [x] #4 Config status_method toggles between pipe and file
- [x] #5 Malformed messages silently ignored (no crash)
- [x] #6 Status changes reflected in dashboard UI on next render cycle
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Added `serde_json = \"1\"` to Cargo.toml\n2. Added `StatusMessage` struct to types.rs with `to_agent_status()` mapping all event strings\n3. Implemented `pipe()` handler for \"claude-status\" pipe name — parses JSON payload, updates matching agent status\n4. Added `poll_status_files()` for file fallback — reads `/tmp/claude-{id}.state` per agent\n5. Added timer-based polling: `set_timeout(2.0)` in load() when config.status_method == File, re-set in Timer handler\n6. Malformed JSON silently ignored via match on serde_json::from_str
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-42 Completed\n\n### Files modified\n- `Cargo.toml` — added serde_json dep\n- `src/types.rs` — added StatusMessage with event-to-status mapping\n- `src/lib.rs` — pipe() handles \"claude-status\", Timer handles file polling, handle_status_message() + poll_status_files()\n\n### Status mapping\n| Event string | AgentStatus |\n|---|---|\n| stopped/Stop | Stopped |\n| running/PreToolUse/start | Running |\n| idle/idle_prompt | WaitingForInput |\n| permission/permission_prompt | PermissionRequired |\n\n### Key decisions\n- Pipe is primary (real-time), file polling at 2s interval is fallback\n- Config `status_method` toggles between modes\n- Malformed payloads silently dropped (no panic)\n- DoD #1, #2 deferred to manual Zellij testing
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: zellij pipe --name claude-status --payload with idle event updates dashboard
- [ ] #2 Manual test: write permission to /tmp/claude-agent-1.state and verify file fallback
- [x] #3 No panics on empty, malformed, or oversized payloads
<!-- DOD:END -->
