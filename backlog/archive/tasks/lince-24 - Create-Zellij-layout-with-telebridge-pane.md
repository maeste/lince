---
id: LINCE-24
title: Create Zellij layout with telebridge pane
status: To Do
assignee: []
created_date: '2026-03-03 14:36'
updated_date: '2026-03-30 16:53'
labels:
  - telebridge
  - zellij
  - layout
milestone: m-6
dependencies: []
references:
  - zellij-setup/three-pane.kdl
  - zellij-setup/zellij-aliases.sh
  - zellij-setup/install.sh
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a new Zellij layout variant to `zellij-setup/` that includes telebridge as a fourth pane (or replaces VoxCode pane for remote-only usage).

**Layout option A — 4 pane (local + remote):**
```
┌─────────────────────────────────┐
│        Claude Code (Sandbox)    │  50% height
├──────────┬──────────┬───────────┤
│ Backlog  │ VoxCode  │Telebridge │  25% each / 33% width
│ Board    │          │ Logs      │
└──────────┴──────────┴───────────┘
```

**Layout option B — 3 pane remote (replace VoxCode):**
```
┌─────────────────────────────────┐
│        Claude Code (Sandbox)    │  50% height
├────────────────┬────────────────┤
│    Backlog     │   Telebridge   │  25% each
│    Board       │   Logs         │
└────────────────┴────────────────┘
```

**Implementation:**
- New layout file: `zellij-setup/three-pane-remote.kdl`
- Telebridge pane runs: `telebridge run` (or `uv run telebridge run`)
- Claude Code pane: `claude-sandbox run` (or `claude` without sandbox)
- Backlog pane: `backlog board`

**Shell alias:**
- `zr3` or `z3r` — launch 3-pane remote layout
- Add to `zellij-aliases.sh`

**Config alignment**: The Zellij layout pane arrangement must match the `target_pane` direction in telebridge's config. E.g., if Claude Code is above telebridge, then `target_pane = "up"`.

**Install script**: Update `install.sh` to offer the remote layout option.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 New KDL layout file for remote-first usage
- [ ] #2 Telebridge pane starts with telebridge run
- [ ] #3 Layout pane directions match config defaults
- [ ] #4 Shell alias added for quick launch
- [ ] #5 Install script updated with new layout option
<!-- AC:END -->
