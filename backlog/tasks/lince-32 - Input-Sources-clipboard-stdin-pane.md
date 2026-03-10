---
id: LINCE-32
title: 'Input Sources (clipboard, stdin, pane)'
status: Done
assignee: []
created_date: '2026-03-10 14:16'
updated_date: '2026-03-10 20:27'
labels:
  - voxtts
  - input
  - clipboard
  - pane
milestone: m-9
dependencies:
  - LINCE-31
references:
  - voxcode/src/voxcode/multiplexer.py
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement multiple input sources: file, clipboard, stdin pipe, tmux/zellij pane capture.

Clipboard: tries wl-paste (Wayland) then xclip (X11).
Stdin: reads from piped stdin (checks sys.stdin.isatty()).
Multiplexer: detect_multiplexer(), capture_tmux_pane() via tmux capture-pane -p, capture_zellij_pane() via zellij action dump-screen.
Adapt multiplexer pattern from voxcode/multiplexer.py.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 reader.py with read_file(), read_clipboard(), read_pane(), read_stdin()
- [ ] #2 read_clipboard(): tries wl-paste (Wayland) then xclip (X11), clear error if neither available
- [ ] #3 read_stdin(): reads from piped stdin (checks sys.stdin.isatty())
- [ ] #4 multiplexer.py: detect_multiplexer(), capture_tmux_pane(), capture_zellij_pane()
- [ ] #5 get_input_text() dispatcher based on CLI args
- [ ] #6 voxtts --clipboard --play works
- [ ] #7 echo hello | voxtts --play works
- [ ] #8 voxtts --pane -o pane.mp3 captures and converts pane content
<!-- AC:END -->
