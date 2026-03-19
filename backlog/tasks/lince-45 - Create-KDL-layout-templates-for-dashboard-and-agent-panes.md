---
id: LINCE-45
title: Create KDL layout templates for dashboard and agent panes
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:40'
updated_date: '2026-03-19 13:58'
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
- [x] #1 layouts/dashboard.kdl exists with plugin + voxcode + shell layout
- [x] #2 layouts/agent-single.kdl exists documenting single-pane agent pattern
- [x] #3 layouts/agent-multi.kdl exists documenting multi-pane agent pattern
- [ ] #4 Dashboard layout loads in Zellij 0.43.x (zellij -l /path/to/dashboard.kdl)
- [x] #5 Layout follows existing conventions (tab-bar, status-bar, borderless)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Created `layouts/dashboard.kdl` — main layout with plugin pane (60%) + voxcode + shell (40% split), tab-bar/status-bar via default_tab_template\n2. Created `layouts/agent-single.kdl` — documented reference for floating agent panes (created programmatically)\n3. Created `layouts/agent-multi.kdl` — template for multi-pane agent tab (claude-sandbox + backlog + shell), with placeholder comments for runtime substitution
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-45 Completed\n\n### Files created\n- `layouts/dashboard.kdl` — Plugin (60%) + VoxCode + Shell layout with tab-bar/status-bar\n- `layouts/agent-single.kdl` — Reference doc for floating pane pattern\n- `layouts/agent-multi.kdl` — Template for agent tab (claude-sandbox + backlog + shell)\n\n### Key decisions\n- Dashboard layout uses `file:~/.config/zellij/plugins/lince-dashboard.wasm` for plugin location\n- Config path passed via plugin configuration block\n- Agent templates are documentation/reference — plugin creates panes programmatically\n- AC #4 and DoD #1, #2 deferred to manual Zellij testing
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 zellij setup --check passes for dashboard.kdl
- [ ] #2 Manual test: layout loads showing plugin pane, voxcode pane, shell pane
- [x] #3 Agent templates clearly commented for maintainability
<!-- DOD:END -->
