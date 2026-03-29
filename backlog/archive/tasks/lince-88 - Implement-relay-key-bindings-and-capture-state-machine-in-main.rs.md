---
id: LINCE-88
title: Implement relay key bindings and capture state machine in main.rs
status: To Do
assignee: []
created_date: '2026-03-25 22:27'
updated_date: '2026-03-26 10:13'
labels:
  - dashboard
  - relay
  - state-machine
milestone: m-12
dependencies: []
references:
  - lince-dashboard/plugin/src/main.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Add the core relay logic to `main.rs`: state field, key bindings (`s`/`S`), capture initiation, and `RunCommandResult` handler for the async pane dump.

**Why**: This is the engine that drives the relay feature — key press → focus source pane → async dump → store captured text.

### Implementation scope

**State field** — Add to `State` struct (after `rename_target`):
```rust
relay_state: Option<RelayState>,
```
Initialize to `None` in `Default` impl.

**Import** — Add `RelayPhase, RelayState` to the `use crate::types` import.

**Key dispatch** — In `handle_key()`, after wizard/name_prompt checks (line ~365):
```rust
if self.relay_state.is_some() {
    return self.handle_relay_key(key);
}
```

**Key bindings** — In the normal key match block:
- `s` → `self.start_relay(50)` (capture last 50 lines, default)
- `S` → `self.start_relay_with_prompt()` (enter LinePrompt phase)

**`start_relay(lines)` method**:
1. Validate: at least 2 agents, source has pane_id
2. Focus source pane via `focus_terminal_pane(pid, true)`
3. Call `config::capture_pane_async(&source_id, lines)`
4. Set `relay_state = Some(RelayState { phase: Capturing { ... }, source_index })`
5. Set status message "Capturing..."

**`start_relay_with_prompt()` method**:
1. Same validations
2. Set `relay_state = Some(RelayState { phase: LinePrompt { input: String::new() }, source_index })`

**`RunCommandResult` handler** — New case for `CMD_CAPTURE_PANE`:
1. Call `show_self(false)` to refocus dashboard after source pane flash
2. On failure (exit_code != 0 or empty stdout): clear relay_state, show error
3. On success: parse stdout as captured text, look up agent name from context's `source_agent_id`
4. Transition phase: `Capturing → DeliveryPending { source_agent_name, captured_text, line_count }`
5. Set status: "Captured N lines from Agent-X. Select target (f/Enter/1-9), Esc cancel"

**Key files**: `plugin/src/main.rs`
**Depends on**: LINCE-87 (types and capture helper)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 relay_state: Option<RelayState> field exists in State struct
- [ ] #2 #2 's' key triggers start_relay(50) — focuses source pane and kicks off async capture
- [ ] #3 #3 'S' key triggers start_relay_with_prompt() — enters LinePrompt phase
- [ ] #4 #4 handle_key() routes to handle_relay_key() when relay_state is Some
- [ ] #5 #5 RunCommandResult for CMD_CAPTURE_PANE transitions Capturing → DeliveryPending with captured text
- [ ] #6 #6 show_self(false) called after capture to refocus dashboard
- [ ] #7 #7 Capture failure (non-zero exit, empty stdout) clears relay_state and shows error
- [ ] #8 #8 Status bar shows appropriate message at each phase
<!-- AC:END -->
