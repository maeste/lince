---
id: LINCE-89
title: >-
  Implement relay key handling: LinePrompt input, DeliveryPending navigation,
  and delivery to target
status: To Do
assignee: []
created_date: '2026-03-25 22:27'
updated_date: '2026-03-26 10:13'
labels:
  - dashboard
  - relay
  - delivery
milestone: m-12
dependencies: []
references:
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/pane_manager.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Implement `handle_relay_key()` and `deliver_relay_to_selected()` — the key handling for each relay phase and the actual delivery of captured text to the target agent pane.

**Why**: After capture, the user needs to navigate to a target agent and deliver the text. This task completes the relay state machine.

### Implementation scope

**`handle_relay_key(key)` method** — dispatches by phase:

**LinePrompt phase**:
- Digit keys (`0-9`): append to input (max 3 chars → 999 lines max)
- `Backspace`: pop last char
- `Enter`: parse input as usize (default 50 if empty, clamped 1-500), call `start_relay(n)`
- `Esc`: cancel, clear relay_state

**Capturing phase**:
- `Esc`: cancel, clear relay_state, show "Relay cancelled"
- All other keys: ignored (async operation in progress)

**DeliveryPending phase**:
- `f` / `Enter`: call `deliver_relay_to_selected()` for currently selected agent
- `1-9`: set selected_index to (digit-1), then `deliver_relay_to_selected()`
- `j` / `Down`: wrap_next navigation (allows picking different target)
- `k` / `Up`: wrap_prev navigation
- `Esc`: cancel, clear relay_state

**`deliver_relay_to_selected()` method**:
1. Take relay_state (move out of Option)
2. Extract source_name, captured_text, line_count from DeliveryPending phase
3. Validate: target != source (prevent self-relay → show error, re-enter DeliveryPending)
4. Validate: target has pane_id
5. Wrap text: `"--- Relay from {source_name} ({line_count} lines) ---\n{captured_text}\n--- End relay ---\n"`
6. Call `write_chars_to_pane_id(&wrapped, PaneId::Terminal(target_pid))` — NO auto-Enter
7. Focus target agent via `pane_manager::focus_agent()`
8. Set `focused_agent` and status message "Relayed N lines from X to Y"
9. Clear relay_state

**Key files**: `plugin/src/main.rs`
**Depends on**: LINCE-88
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 LinePrompt: digit keys build line count, Enter starts capture, Esc cancels
- [ ] #2 #2 Capturing: only Esc cancels, all other keys ignored
- [ ] #3 #3 DeliveryPending: f/Enter delivers to selected agent, 1-9 delivers to agent by index
- [ ] #4 #4 DeliveryPending: j/k navigation works to select different target
- [ ] #5 #5 Self-relay prevented — error shown, stays in DeliveryPending
- [ ] #6 #6 Target without pane_id shows error
- [ ] #7 #7 Captured text wrapped with header/footer: '--- Relay from {name} ({N} lines) ---'
- [ ] #8 #8 Text written via write_chars_to_pane_id with NO trailing Enter/newline submission
- [ ] #9 #9 Target agent pane focused after delivery
- [ ] #10 #10 Esc cancels at any phase and returns to normal dashboard
<!-- AC:END -->
