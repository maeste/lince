---
id: LINCE-48
title: 'Display detailed agent status with token usage, active tool, and elapsed time'
status: To Do
assignee: []
created_date: '2026-03-19 10:40'
updated_date: '2026-03-19 10:45'
labels:
  - dashboard
  - status
  - enhancement
milestone: m-11
dependencies:
  - LINCE-42
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend hooks and dashboard to show richer agent info: token usage, active tool name, session elapsed time, errors.

## Implementation Plan

1. Extend `StatusMessage` in `types.rs` with optional fields: `tool_name`, `tokens_in`, `tokens_out`, `error`
2. Extend `AgentInfo` with: `token_usage: (u64, u64)`, `current_tool: Option<String>`, `started_at: String`, `last_error: Option<String>`
3. Update `hooks/claude-status-hook.sh` to extract tool name from `PreToolUse` stdin JSON field
4. Add agent detail panel: `Enter` on selected shows expanded info panel (not focus). `f` still focuses pane.
5. Elapsed time via timer: store `started_at` timestamp, calculate delta on each render
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Hook reports tool name in payload for PreToolUse events
- [ ] #2 Dashboard table shows token count column
- [ ] #3 Agent detail panel shows full status info
- [ ] #4 Elapsed time updates every timer tick
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: trigger PreToolUse hook, verify tool name in dashboard
- [ ] #2 Detail panel renders correctly at various pane sizes
<!-- DOD:END -->
