---
id: LINCE-41
title: 'Implement pane focus, hide, and show for agent pane switching'
status: To Do
assignee: []
created_date: '2026-03-19 10:38'
labels:
  - dashboard
  - pane
  - rust
milestone: m-10
dependencies:
  - LINCE-39
  - LINCE-40
references:
  - zellij-setup/configs/config.kdl (keybindings)
  - voxcode/src/voxcode/zellij_bridge.py (pane focus pattern)
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let user show/hide agent panes and switch between them from the dashboard. Agent panes are hidden by default; the dashboard provides commands to focus, unfocus, and cycle between agents.

## Implementation Plan

1. Create `src/pane_manager.rs`
2. **focus_agent(state, agent_id)**:
   - If `focus_mode == Floating`: `show_pane_with_id(pane_id)` then `focus_terminal_pane(pane_id, true)`. Set `state.focused_agent = Some(agent_id)`.
   - If `focus_mode == Replace`: `focus_terminal_pane(pane_id, false)` (embedded). For multi-pane agents, switch to their tab.
3. **unfocus_agent(state)**:
   - Floating: `hide_pane_with_id(pane_id)`, clear `state.focused_agent`.
   - Replace: `go_to_tab(dashboard_tab_index)`.
4. **cycle_selection(state, direction)**: Update `state.selected_index` wrapping around `state.agents.len()`
5. **Key mappings** in `update()`:
   - `f` or `Enter` → focus selected agent
   - `Escape` or `d` → unfocus (hide agent pane, return to dashboard)
   - `Tab`/`Down`/`j` → cycle selection forward
   - `Shift+Tab`/`Up`/`k` → cycle backward (when not confirming kill)
   - `]` → focus next agent directly, `[` → focus previous
6. Track `dashboard_tab_index` in State (set during `load()`)
7. Visual feedback: focused row shows `[FOCUSED]` badge, unfocused shows `[HIDDEN]`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 src/pane_manager.rs exists with focus/unfocus/cycle functions
- [ ] #2 f/Enter shows the selected agent pane (floating or tab switch)
- [ ] #3 Escape hides agent pane and returns to dashboard view
- [ ] #4 Tab/arrows cycle through agent list with visual highlighting
- [ ] #5 ]/[ directly switch between agent panes
- [ ] #6 Both Floating and Replace focus modes work correctly
- [ ] #7 Focused agent is visually indicated in the dashboard table
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: spawn 2 agents, focus agent 1, verify shown, Escape hides, focus agent 2 works
- [ ] #2 No pane state leaks (hidden panes stay hidden, shown panes can be hidden)
- [ ] #3 Key conflicts with Zellij keybindings documented
<!-- DOD:END -->
