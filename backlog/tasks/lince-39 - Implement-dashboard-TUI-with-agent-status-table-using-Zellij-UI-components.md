---
id: LINCE-39
title: Implement dashboard TUI with agent status table using Zellij UI components
status: To Do
assignee: []
created_date: '2026-03-19 10:38'
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
- [ ] #1 src/dashboard.rs and src/types.rs exist
- [ ] #2 Header shows title and agent count
- [ ] #3 Table renders with color-coded status per agent
- [ ] #4 Selected agent row is visually highlighted (reverse video)
- [ ] #5 Empty state shows helpful message
- [ ] #6 Command bar shows available keybindings
- [ ] #7 Rendering adapts to terminal dimensions (no overflow/panic on small sizes)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Plugin displays correct dashboard UI in Zellij at various pane sizes (tested at 80x24 and 120x40)
- [ ] #2 No ANSI artifacts or overflow when pane is resized
- [ ] #3 Colors follow consistent scheme documented in types.rs
<!-- DOD:END -->
