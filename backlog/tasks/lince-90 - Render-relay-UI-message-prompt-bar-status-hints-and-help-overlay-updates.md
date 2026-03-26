---
id: LINCE-90
title: 'Render relay UI: message prompt bar, status hints, and help overlay updates'
status: To Do
assignee: []
created_date: '2026-03-26 10:15'
labels:
  - dashboard
  - relay
  - TUI
  - rendering
milestone: m-12
dependencies:
  - LINCE-88
references:
  - lince-dashboard/plugin/src/dashboard.rs
  - lince-dashboard/plugin/src/main.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Update `dashboard.rs` and `main.rs` render() to display relay-specific UI: the message count prompt, delivery-pending status hints, and help overlay documentation.

**Why**: The user needs visual feedback at each relay phase — what's happening, what keys are available, and how to proceed or cancel.

### Implementation scope

**In `plugin/src/dashboard.rs`**:

1. **`render_relay_message_prompt(input, cols)`** — new function, blue status bar (like name prompt bar at ~line 526):
   ```
   [44m Relay: Messages to capture (1-9): [1█]  [Enter] OK  [Esc] Cancel [0m
   ```
   - Shows default "1" in dim when input is empty
   - Shows cursor block after input
   - Same visual pattern as `render_name_prompt_bar`

2. **Update `render_status_bar` signature** — add `relay_pending: bool`:
   - When true, show: `s=Relay  f/Enter=Deliver  j/k=Nav  1-9=Quick  Esc=Cancel`
   - When false, existing behavior

3. **Update `render_dashboard` signature** — add `relay_phase: Option<&RelayPhase>`:
   - `MessagePrompt`: render `render_relay_message_prompt` instead of normal status bar
   - `DeliveryPending`: pass `relay_pending: true` to `render_status_bar`
   - `Extracting`: existing status_message "Extracting..." suffices

4. **Update help overlay** (`render_help_overlay`) — add section:
   ```
   Relay
     s          Relay last message to another agent
     S          Relay N messages (prompt for count)
   ```

**In `plugin/src/main.rs` render()**:
- Extract `relay_phase` from `self.relay_state.as_ref().map(|r| &r.phase)`
- Pass to `render_dashboard`

**Key files**: `plugin/src/dashboard.rs`, `plugin/src/main.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 render_relay_message_prompt() renders blue bar with message count input (1-9) and cursor
- [ ] #2 #2 Empty input shows default '1' in dim style
- [ ] #3 #3 Status bar shows relay-specific key hints during DeliveryPending phase
- [ ] #4 #4 render_dashboard accepts relay_phase parameter and routes to correct renderer
- [ ] #5 #5 Help overlay includes s/S key descriptions under 'Relay' section
- [ ] #6 #6 Extracting phase shows 'Extracting...' via existing status_message mechanism
- [ ] #7 #7 DeliveryPending shows 'Extracted N messages from X. Select target...' in status bar
<!-- AC:END -->
