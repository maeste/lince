---
id: LINCE-89
title: 'Implement relay state machine, key bindings, and message delivery in main.rs'
status: To Do
assignee: []
created_date: '2026-03-26 10:15'
labels:
  - dashboard
  - relay
  - state-machine
  - delivery
milestone: m-12
dependencies:
  - LINCE-88
references:
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/pane_manager.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Add the full relay logic to `main.rs`: state field, key bindings (`s`/`S`), state machine dispatch, extraction result handler, and delivery to target agent pane.

**Why**: This is the core engine — key press → extract messages from transcript → deliver to target pane. Combines the state machine, key handling, and delivery in a single task since they're tightly coupled in main.rs.

### Implementation scope

**State field** — Add to `State` struct (after `rename_target`):
```rust
relay_state: Option<RelayState>,
```
Initialize to `None` in `Default` impl. Add `RelayPhase, RelayState` to imports.

**Key dispatch** — In `handle_key()`, after wizard/name_prompt checks:
```rust
if self.relay_state.is_some() {
    return self.handle_relay_key(key);
}
```

**Normal key bindings**:
- `s` → `self.start_relay(1)` — relay last 1 message (default)
- `S` → `self.start_relay_with_prompt()` — enter MessagePrompt phase

**`start_relay(count)` method**:
1. Validate: agent exists, has `transcript_path` (else "Transcript not available for this agent type")
2. Validate: at least 2 agents (else "Need 2+ agents to relay")
3. Call `config::extract_transcript_async(&agent.id, &transcript_path, count)`
4. Set relay_state to `Extracting { source_agent_id, source_agent_name, message_count }`
5. Status: "Extracting..."

**`start_relay_with_prompt()`**: Same validations, then set `MessagePrompt { input: "" }`

**`handle_relay_key(key)` method** — dispatches by phase:

*MessagePrompt*: digit `1-9` sets input (single digit), Enter → `start_relay(n)`, Esc → cancel

*Extracting*: Esc → cancel, all else ignored

*DeliveryPending*: `f`/`Enter` → deliver to selected, `1-9` → select+deliver, `j/k` → navigate, Esc → cancel

**`deliver_relay_to_selected()` method**:
1. Take relay_state, extract DeliveryPending fields
2. Validate: target != source (prevent self-relay, re-enter DeliveryPending)
3. Validate: target has pane_id
4. Wrap: `"--- Relay from {name} ({N} messages) ---\n{text}\n--- End relay ---\n"`
5. `write_chars_to_pane_id(&wrapped, PaneId::Terminal(pid))` — NO auto-Enter
6. Focus target via `pane_manager::focus_agent()`
7. Status: "Relayed N messages from X to Y"

**RunCommandResult handler** — New case for `CMD_EXTRACT_TRANSCRIPT`:
1. On failure/empty/error marker: clear relay_state, show error
2. On success: transition `Extracting → DeliveryPending` with captured text
3. Status: "Extracted N messages from X. Select target (f/Enter/1-9), Esc cancel"

No pane focus needed during extraction (reads file directly, not screen).

**Key files**: `plugin/src/main.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 relay_state: Option<RelayState> field in State, initialized to None
- [ ] #2 #2 's' triggers start_relay(1) — extracts last 1 message from transcript
- [ ] #3 #3 'S' enters MessagePrompt phase for user to pick count 1-9
- [ ] #4 #4 handle_key routes to handle_relay_key when relay_state is Some
- [ ] #5 #5 MessagePrompt: single digit 1-9, Enter starts extraction, Esc cancels
- [ ] #6 #6 Extracting: only Esc cancels, other keys ignored
- [ ] #7 #7 DeliveryPending: f/Enter delivers to selected, 1-9 quick deliver, j/k navigate, Esc cancels
- [ ] #8 #8 Self-relay prevented — error shown, stays in DeliveryPending
- [ ] #9 #9 Text wrapped with header/footer, written via write_chars_to_pane_id with NO auto-Enter
- [ ] #10 #10 Target agent pane focused after delivery
- [ ] #11 #11 RunCommandResult for CMD_EXTRACT_TRANSCRIPT transitions Extracting → DeliveryPending
- [ ] #12 #12 Agents without transcript_path get 'not available' message on s/S
<!-- AC:END -->
