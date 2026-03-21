---
id: LINCE-53
title: Track running subagents and show composite status in dashboard
status: Done
assignee: []
created_date: '2026-03-19 21:40'
updated_date: '2026-03-19 22:17'
labels:
  - dashboard
  - status
  - hooks
  - enhancement
milestone: m-11
dependencies:
  - LINCE-42
references:
  - lince-dashboard/hooks/claude-status-hook.sh
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/dashboard.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When Claude Code's main agent is idle (accepting input) but has background subagents running, the dashboard currently shows just "INPUT". There is no visual indication that background work is still in progress or that the user can type while subagents are active.

## Problem

Claude Code fires `SubagentStart` and `SubagentStop` hook events when subagents are launched/completed. These events include `agent_type` (e.g., "Explore", "Plan", "general-purpose") and a subagent-specific `agent_id`. The current hook script (`claude-status-hook.sh`) ignores these events entirely.

The user needs to see a composite status like `INPUT · 3⚙` that communicates two facts simultaneously:
1. The main agent accepts input (yellow "INPUT")
2. N background subagents are still working (cyan suffix)

## Design Decisions

- **Subagent count is orthogonal to agent status**: No new `AgentStatus` enum variant needed. `running_subagents: u32` is tracked as a separate field on `AgentInfo`, and the rendering layer composes the display.
- **Counter-based tracking**: Increment on `SubagentStart`, decrement on `SubagentStop`, reset to 0 on agent `Stop` (safety net).
- **Backward compatible**: If no subagent events arrive, behavior is unchanged.

## Files to Modify

1. **`lince-dashboard/hooks/claude-status-hook.sh`** — Add `SubagentStart` and `SubagentStop` cases to the event mapping. Extract `agent_type` from stdin JSON (via jq/regex fallback). Send events as `"subagent_start"` / `"subagent_stop"` with a `subagent_type` field in the JSON payload.

2. **`lince-dashboard/plugin/src/types.rs`** — Add `subagent_type: Option<String>` to `StatusMessage`. Add `running_subagents: u32` to `AgentInfo` (default 0).

3. **`lince-dashboard/plugin/src/main.rs`** — In `handle_status_message()`: on `"subagent_start"` increment `running_subagents`, on `"subagent_stop"` decrement (saturating to 0), on `"stopped"` reset to 0.

4. **`lince-dashboard/plugin/src/dashboard.rs`** — In status column rendering: when `status == WaitingForInput && running_subagents > 0`, display `INPUT · N⚙` (yellow + cyan suffix). When `status == Running && running_subagents > 0`, display `RUNNING · N⚙`. When `running_subagents == 0`, render as before.

## Hook Event Payloads (from Claude Code)

**SubagentStart** stdin JSON:
```json
{"hook_event_name": "SubagentStart", "agent_id": "subagent-abc", "agent_type": "Explore", "session_id": "..."}
```

**SubagentStop** stdin JSON:
```json
{"hook_event_name": "SubagentStop", "agent_id": "subagent-abc", "agent_type": "Explore", "session_id": "...", "agent_transcript_path": "...", "last_assistant_message": "..."}
```

Note: The `agent_id` in these events refers to the subagent, NOT the parent agent. The parent agent is identified by `LINCE_AGENT_ID` env var (set by the dashboard at spawn time).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Hook script handles SubagentStart events: extracts agent_type from stdin JSON and sends subagent_start event via zellij pipe with subagent_type field
- [x] #2 Hook script handles SubagentStop events: sends subagent_stop event via zellij pipe
- [x] #3 Dashboard increments running_subagents count on subagent_start event and decrements (min 0) on subagent_stop event
- [x] #4 Dashboard resets running_subagents to 0 when agent status becomes Stopped (safety net)
- [x] #5 When agent status is WaitingForInput and running_subagents > 0, status column displays composite format (e.g. INPUT · N⚙) with distinct color for the subagent suffix
- [x] #6 When agent status is Running and running_subagents > 0, status column displays composite format (e.g. RUNNING · N⚙)
- [x] #7 When running_subagents is 0, status column renders identically to current behavior (no regression)
- [x] #8 Hook script exits 0 quickly for SubagentStart/SubagentStop events (never blocks Claude Code)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented subagent-aware composite status in the TUI dashboard.

**Hook script** (`claude-status-hook.sh`):
- Added `SubagentStart` → `subagent_start` and `SubagentStop` → `subagent_stop` event mapping
- Extracts `agent_type` from stdin JSON and includes it as `subagent_type` in the pipe payload
- Both jq and bash-fallback payload builders updated

**Types** (`types.rs`):
- Added `subagent_type: Option<String>` to `StatusMessage`
- Added `running_subagents: u32` to `AgentInfo`

**Plugin logic** (`main.rs`):
- `handle_status_message()` increments counter on `subagent_start`, decrements (saturating) on `subagent_stop`
- Resets `running_subagents = 0` on agent `Stopped` as safety net
- Subagent events return early without changing agent status (orthogonal tracking)

**Rendering** (`dashboard.rs`):
- When `running_subagents > 0`, appends cyan ` N⚙` suffix after status label in both selected and normal rows
- Detail panel shows subagent count inline with tool info
- When `running_subagents == 0`, rendering is identical to before (no regression)
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: launch Claude agent with background subagents, verify status transitions INPUT → INPUT · N⚙ → INPUT as subagents complete
- [x] #2 WASM plugin builds successfully: cargo build --target wasm32-wasip1
<!-- DOD:END -->
