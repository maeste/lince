---
id: LINCE-42
title: Implement agent status detection via zellij pipe with file fallback
status: To Do
assignee: []
created_date: '2026-03-19 10:39'
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
- [ ] #1 Pipe handler parses claude-status messages and updates correct agent status
- [ ] #2 All event types (Stop, PreToolUse, idle_prompt, permission_prompt) map correctly
- [ ] #3 File fallback reads /tmp/claude-{id}.state every 2 seconds
- [ ] #4 Config status_method toggles between pipe and file
- [ ] #5 Malformed messages silently ignored (no crash)
- [ ] #6 Status changes reflected in dashboard UI on next render cycle
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: zellij pipe --name claude-status --payload with idle event updates dashboard
- [ ] #2 Manual test: write permission to /tmp/claude-agent-1.state and verify file fallback
- [ ] #3 No panics on empty, malformed, or oversized payloads
<!-- DOD:END -->
