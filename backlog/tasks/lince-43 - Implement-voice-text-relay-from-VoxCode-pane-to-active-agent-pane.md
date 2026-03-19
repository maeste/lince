---
id: LINCE-43
title: Implement voice text relay from VoxCode pane to active agent pane
status: To Do
assignee: []
created_date: '2026-03-19 10:39'
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
- [ ] #1 Plugin handles voxcode-text pipe messages
- [ ] #2 Text forwarded to focused/selected agent pane via write_chars_to_pane_id()
- [ ] #3 Missing agent shows error message in command bar (auto-clears after 3s)
- [ ] #4 i key enters input mode, Escape exits
- [ ] #5 In input mode keystrokes forwarded to agent pane
- [ ] #6 Mode indicator visible in command bar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: zellij pipe --name voxcode-text --payload 'hello world' shows text in agent terminal
- [ ] #2 Manual test: i key, type chars, verify in agent pane, Escape restores dashboard commands
- [ ] #3 No text loss or double-sending
<!-- DOD:END -->
