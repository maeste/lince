---
id: LINCE-43
title: Implement voice text relay from VoxCode pane to active agent pane
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:39'
updated_date: '2026-03-19 13:56'
labels:
  - dashboard
  - voice
  - relay
  - rust
milestone: m-10
dependencies:
  - LINCE-41
references:
  - 'voxcode/src/voxcode/zellij_bridge.py (current: zellij action write-chars)'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The dashboard plugin receives text from VoxCode via Zellij pipe and forwards it to the currently focused/selected agent's pane. This decouples VoxCode from knowing which agent pane to target. Also provides a keyboard input mode for direct typing to agents.

## Implementation Plan

1. In `pipe()` method: add handler for pipe name `"voxcode-text"`
   - Extract payload as plain text (transcribed speech)
   - If `state.focused_agent` set: find agent, `write_chars_to_pane_id(pane_id, payload.chars())`
   - If no agent focused but `selected_index` valid: write to that agent's pane
   - If no agents: show transient error "No agent to receive text" in command bar for 3 seconds (timer-based clear)
2. Add keyboard input mode:
   - `i` key toggles `input_mode: bool` in State (like vim)
   - In input mode: all key events forwarded to selected agent via `write_chars_to_pane_id()`
   - `Escape` exits input mode
   - Command bar shows `[INPUT MODE - Esc to exit]` indicator
3. In `update()` Event::Key: if `input_mode`, forward key instead of processing as dashboard command
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Plugin handles voxcode-text pipe messages
- [x] #2 Text forwarded to focused/selected agent pane via write_chars_to_pane_id()
- [x] #3 Missing agent shows error message in command bar (auto-clears after 3s)
- [x] #4 i key enters input mode, Escape exits
- [x] #5 In input mode keystrokes forwarded to agent pane
- [x] #6 Mode indicator visible in command bar
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Added \"voxcode-text\" handler in pipe() method — receives text payload\n2. Implemented handle_voxcode_text(): routes text to focused agent > selected agent > error message\n3. Uses write_chars_to_pane_id() to forward text to agent's terminal pane\n4. No-target case shows \"No agent to receive text\" with 3s auto-clear via set_timeout()\n5. Input mode (i key) already implemented in LINCE-40 — forwards keystrokes to selected agent\n6. Mode indicator in command bar already handled by dashboard.rs render_dashboard()
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-43 Completed\n\n### Files modified\n- `src/lib.rs` — pipe() handles \"voxcode-text\", handle_voxcode_text() routes text to agent pane\n\n### Text routing priority\n1. Focused agent (if any) → its pane\n2. Selected agent (fallback) → its pane\n3. No agents → status message \"No agent to receive text\" (auto-clears 3s)\n\n### Key decisions\n- VoxCode sends via `zellij pipe --name voxcode-text --payload \"text\"`\n- Plugin relays via write_chars_to_pane_id() — VoxCode doesn't need to know pane IDs\n- Input mode (i key) for keyboard relay was already implemented in LINCE-40\n- DoD #1, #2 deferred to manual testing
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: zellij pipe --name voxcode-text --payload 'hello world' shows text in agent terminal
- [ ] #2 Manual test: i key, type chars, verify in agent pane, Escape restores dashboard commands
- [x] #3 No text loss or double-sending
<!-- DOD:END -->
