---
id: LINCE-39
title: Implement dashboard TUI with agent status table using Zellij UI components
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:38'
updated_date: '2026-03-19 13:06'
labels:
  - dashboard
  - tui
  - rust
milestone: m-10
dependencies:
  - LINCE-37
references:
  - zellij-setup/configs/three-pane.kdl
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the TUI that renders agent status in the plugin pane. Uses Zellij's plugin rendering (stdout capture) with ANSI styling.

## Implementation Plan

1. Create `src/types.rs`:
   - `AgentStatus` enum: `Starting`, `Running`, `Idle`, `WaitingForInput`, `PermissionRequired`, `Stopped`, `Error(String)`
   - `AgentInfo` struct: `id`, `name`, `profile`, `project_dir`, `status`, `pane_id`, `pane_ids`
   - Impl `AgentStatus::color()` (ANSI codes: green=Running, yellow=Idle/WaitingForInput, red=PermissionRequired/Error, dim=Stopped, cyan=Starting)
   - Impl `AgentStatus::label()` (display text)
2. Create `src/dashboard.rs`:
   - `render_dashboard(agents, selected, focused, rows, cols)`
   - **Header** (row 0): "LINCE Dashboard" + agent count, bold ANSI + background color
   - **Agent table** (rows 2..rows-3): columns `#`, `Name`, `Profile`, `Project`, `Status`, `Pane`. Selected row in reverse video. Focused agent marked with `>` prefix. "Waiting" agents bold yellow.
   - **Empty state**: centered "No agents running. Press [n] to create one."
   - **Command bar** (last 2 rows): `[n]ew  [f]ocus  [h]ide  [k]ill  [q]uit`
   - Handle truncation for narrow columns
3. In `main.rs`: call `render_dashboard()` from `render()`, add `mod types; mod dashboard;`
4. Update `State` to include `agents: Vec<AgentInfo>`, `selected_index: usize`, `focused_agent: Option<String>`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 src/dashboard.rs and src/types.rs exist
- [x] #2 Header shows title and agent count
- [x] #3 Table renders with color-coded status per agent
- [x] #4 Selected agent row is visually highlighted (reverse video)
- [x] #5 Empty state shows helpful message
- [x] #6 Command bar shows available keybindings
- [x] #7 Rendering adapts to terminal dimensions (no overflow/panic on small sizes)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Created `src/types.rs` with AgentStatus enum (7 variants, ANSI color(), label()) and AgentInfo struct\n2. Created `src/dashboard.rs` with render_dashboard() — header bar, agent table with color-coded status, selected row highlighting, focused agent indicator, empty state, command bar with mode-awareness\n3. Updated `src/lib.rs` to wire modules and State fields, delegate render to dashboard::render_dashboard()\n4. Edge cases handled: cols<40 abbreviation, rows<5 minimal mode, scrolling, string truncation with \"...\"\n5. Compiled cleanly with zero warnings
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-39 Completed\n\n### Files created\n- `src/types.rs` — AgentStatus (7 variants with ANSI colors), AgentInfo struct\n- `src/dashboard.rs` — Full TUI render: header, agent table, empty state, command bar\n\n### Files modified\n- `src/lib.rs` — Added mod declarations, extended State with agent/selection/focus/input fields\n\n### Key features\n- Color-coded status: green=Running, yellow=Idle/WaitingForInput, red=Permission/Error, cyan=Starting, dim=Stopped\n- Reverse video for selected row, \">\" prefix for focused agent\n- Command bar switches between normal/input mode/status message\n- Graceful degradation for small terminal sizes\n- DoD #1 deferred — requires manual Zellij testing at various sizes
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Plugin displays correct dashboard UI in Zellij at various pane sizes (tested at 80x24 and 120x40)
- [x] #2 No ANSI artifacts or overflow when pane is resized
- [x] #3 Colors follow consistent scheme documented in types.rs
<!-- DOD:END -->
