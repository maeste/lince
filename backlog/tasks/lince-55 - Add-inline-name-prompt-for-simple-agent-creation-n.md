---
id: LINCE-55
title: Add inline name prompt for simple agent creation ('n')
status: Done
assignee: []
created_date: '2026-03-19 22:07'
updated_date: '2026-03-20 08:58'
labels:
  - dashboard
  - ui
  - enhancement
milestone: m-11
dependencies: []
references:
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/dashboard.rs
  - lince-dashboard/plugin/src/types.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When pressing 'n' to create a simple agent, the agent is spawned immediately with an auto-generated name (`agent-N`). The user has no opportunity to give it a meaningful name without using the full wizard ('N'). For swimlane-based workflows, descriptive names are important for quickly identifying agents.

## Problem

The 'n' key handler in `main.rs` directly spawns an agent with defaults. The wizard ('N') has a full Name step but is heavyweight for quick agent creation. There is no middle ground — a minimal inline prompt that asks just for the name.

## Design Decisions

- **Overlay prompt, not mode switch**: A small prompt renders over the bottom of the dashboard (similar to a command palette). No full-screen mode change.
- **Default name pre-filled**: The prompt shows `agent-N` (next available number) as default text. User can accept with Enter or type a custom name.
- **Esc cancels**: Returns to normal mode without spawning.
- **Config defaults**: Profile and project_dir come from config defaults (same as current 'n' behavior). Only the name is prompted.
- **Input state isolation**: Key events are routed to the prompt handler while it's active, preventing accidental agent operations.

## Files to Modify

1. **`lince-dashboard/plugin/src/types.rs`**
   - Add `NamePromptState` struct:
     ```rust
     pub struct NamePromptState {
         pub input: String,
         pub cursor_pos: usize,
         pub default_name: String,
     }
     ```
   - Add constructor `NamePromptState::new(default_name: String)` that sets input to empty and stores default

2. **`lince-dashboard/plugin/src/main.rs`**
   - Add `name_prompt: Option<NamePromptState>` field to State
   - Change 'n' key handler: instead of spawning directly, compute next `agent-N` name and set `self.name_prompt = Some(NamePromptState::new(default_name))`
   - Add `handle_name_prompt_key(&mut self, key: KeyEvent)` method:
     - Enter → spawn agent with `input` if non-empty, else `default_name`; clear prompt
     - Esc → clear prompt, return to normal mode
     - Backspace → remove last char from input
     - Char(c) → append to input
   - In `update()` key routing: if `name_prompt.is_some()`, route to `handle_name_prompt_key()` instead of normal handlers
   - In `render()`: if `name_prompt.is_some()`, call `render_name_prompt()`

3. **`lince-dashboard/plugin/src/dashboard.rs`**
   - Add `render_name_prompt(state: &NamePromptState, rows: usize, cols: usize)` function:
     - Renders a 1-2 line overlay at the bottom of the screen
     - Shows: `Name: [user_input|]` with cursor indicator
     - Shows default name hint: `(default: agent-N)` in dim text
     - Background color distinct from dashboard (e.g., dark blue bar)

## Visual Layout

```
┌─────────────────────────────────────────────┐
│ ... normal dashboard content ...            │
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│ Name: my-agent█          (default: agent-3) │  ← overlay prompt
└─────────────────────────────────────────────┘
```

## Edge Cases

- Empty input + Enter → uses default name
- Name collision with existing agent → append suffix (e.g., agent-3-2) or let spawn handle it
- Prompt active during status update → prompt stays visible, status updates render behind it
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Pressing 'n' shows an inline name prompt overlay at the bottom of the dashboard instead of immediately spawning an agent
- [x] #2 The prompt displays a pre-computed default name (agent-N) as hint text
- [x] #3 Typing characters appends to the name input; Backspace deletes last character
- [x] #4 Pressing Enter spawns the agent with the typed name (or default if input is empty) using config defaults for profile and project_dir
- [x] #5 Pressing Esc cancels the prompt and returns to normal dashboard mode without spawning
- [x] #6 While the prompt is active, other key bindings (kill, wizard, quit) are not triggered
- [x] #7 Dashboard status updates continue rendering behind the prompt overlay
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Replaced direct spawn on 'n' with inline name prompt. Added NamePromptState type, handle_name_prompt_key() for Enter/Esc/Backspace/Char input, render_name_prompt_bar() with blue background overlay replacing status bar. Default name shown as dim placeholder. Enter spawns via spawn_agent_custom(), Esc cancels. Dashboard continues rendering behind the prompt.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Manual test: press 'n', type a custom name, press Enter — verify agent spawns with that name
- [x] #2 Manual test: press 'n', press Enter without typing — verify agent spawns with default name
- [x] #3 Manual test: press 'n', press Esc — verify no agent is spawned
- [x] #4 WASM plugin builds successfully: cargo build --target wasm32-wasip1
<!-- DOD:END -->
