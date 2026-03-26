---
id: LINCE-90
title: 'Render relay UI: line prompt bar, status hints, and help overlay updates'
status: To Do
assignee: []
created_date: '2026-03-25 22:28'
updated_date: '2026-03-26 10:13'
labels:
  - dashboard
  - relay
  - TUI
  - rendering
milestone: m-12
dependencies: []
references:
  - lince-dashboard/plugin/src/dashboard.rs
  - lince-dashboard/plugin/src/main.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Update `dashboard.rs` and the `render()` method in `main.rs` to display relay-specific UI: the line count prompt, delivery-pending status hints, and help overlay documentation.

**Why**: The user needs visual feedback at each relay phase — what's happening, what keys are available, and how to proceed or cancel.

### Implementation scope

**In `plugin/src/dashboard.rs`**:

1. **`render_relay_line_prompt(input, cols)`** — new function, blue status bar (like name prompt):
   ```
   [44m Relay: Lines to capture: [30█]  [Enter] OK  [Esc] Cancel [0m
   ```
   - Shows default "30" in dim when input is empty
   - Shows cursor block after input
   - Follows same pattern as existing `render_name_prompt_bar()` (dashboard.rs ~line 526)

2. **Update `render_status_bar` signature** — add `relay_pending: bool` parameter:
   - When true, show relay-specific key hints: `f/Enter=Deliver  j/k=Nav  1-9=Quick deliver  Esc=Cancel`
   - When false, existing behavior unchanged

3. **Update `render_dashboard` signature** — add `relay_phase: Option<&RelayPhase>` parameter:
   - If `LinePrompt`: render `render_relay_line_prompt` instead of normal status bar
   - If `DeliveryPending`: pass `relay_pending: true` to `render_status_bar`
   - If `Capturing`: show "Capturing..." in status (already handled via status_message)

4. **Update help overlay** (`render_help_overlay`) — add relay section:
   ```
   Relay
     s          Relay last 50 lines to another agent
     S          Relay N lines (prompt for count)
   ```

**In `plugin/src/main.rs` `render()` method**:
- Extract `relay_phase` from `self.relay_state.as_ref().map(|r| &r.phase)`
- Pass to `render_dashboard` as new parameter

**Key files**: `plugin/src/dashboard.rs`, `plugin/src/main.rs`
**Depends on**: LINCE-88 (relay_state exists in State)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 render_relay_line_prompt() renders blue bar with line count input and cursor
- [ ] #2 #2 Empty input shows default '50' in dim style
- [ ] #3 #3 Status bar shows relay-specific key hints during DeliveryPending phase
- [ ] #4 #4 render_dashboard accepts relay_phase parameter and routes to correct renderer
- [ ] #5 #5 Help overlay (?) includes s/S key descriptions under 'Relay' section
- [ ] #6 #6 Capturing phase shows 'Capturing...' status (via existing status_message mechanism)
- [ ] #7 #7 DeliveryPending shows 'Captured N lines from X. Select target...' in status bar
<!-- AC:END -->
