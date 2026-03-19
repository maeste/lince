---
id: LINCE-45
title: Create KDL layout templates for dashboard and agent panes
status: To Do
assignee: []
created_date: '2026-03-19 10:40'
labels:
  - dashboard
  - layouts
  - zellij
milestone: m-10
dependencies: []
references:
  - zellij-setup/configs/three-pane.kdl
  - zellij-setup/configs/config.kdl
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create Zellij KDL layout files for the dashboard main view and agent pane templates.

## Implementation Plan

1. Create `lince-dashboard/layouts/dashboard.kdl`:
   - `default_tab_template` with tab-bar (top, borderless) and status-bar (bottom, borderless) matching `zellij-setup/configs/three-pane.kdl` pattern
   - Tab "dashboard" with horizontal split:
     - Plugin pane (60%): `plugin location="file:~/.config/zellij/plugins/lince-dashboard.wasm" { config_path "~/.config/lince-dashboard/config.toml" }`
     - Bottom split (40%) vertical:
       - VoxCode pane (50%): `command "voxcode"` with appropriate args
       - Shell pane (50%): empty pane for general use
   - Layout diagram:
     ```
     ┌───────────────────────────────────┐
     │ tab-bar                           │
     ├───────────────────────────────────┤
     │ Dashboard Plugin (60%)            │
     ├─────────────────┬─────────────────┤
     │ VoxCode (20%)   │ Shell (20%)     │
     ├─────────────────┴─────────────────┤
     │ status-bar                        │
     └───────────────────────────────────┘
     ```
2. Create `lince-dashboard/layouts/agent-single.kdl`:
   - Comment-documented template for a single floating command pane
   - The plugin creates these programmatically; this file serves as reference
3. Create `lince-dashboard/layouts/agent-multi.kdl`:
   - Template mirroring `three-pane.kdl` pattern: claude-sandbox (50%) top, backlog board (25%) + shell (25%) bottom
   - Placeholder comments for command/args substitution (plugin constructs string dynamically via `new_tab_with_layout()`)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 layouts/dashboard.kdl exists with plugin + voxcode + shell layout
- [ ] #2 layouts/agent-single.kdl exists documenting single-pane agent pattern
- [ ] #3 layouts/agent-multi.kdl exists documenting multi-pane agent pattern
- [ ] #4 Dashboard layout loads in Zellij 0.43.x (zellij -l /path/to/dashboard.kdl)
- [ ] #5 Layout follows existing conventions (tab-bar, status-bar, borderless)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 zellij setup --check passes for dashboard.kdl
- [ ] #2 Manual test: layout loads showing plugin pane, voxcode pane, shell pane
- [ ] #3 Agent templates clearly commented for maintainability
<!-- DOD:END -->
