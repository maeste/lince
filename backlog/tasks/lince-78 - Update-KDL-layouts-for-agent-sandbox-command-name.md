---
id: LINCE-78
title: Update KDL layouts for agent-sandbox command name
status: Done
assignee: []
created_date: '2026-03-25 09:19'
updated_date: '2026-03-25 09:26'
labels:
  - layouts
  - rename
milestone: m-12
dependencies:
  - LINCE-74
references:
  - lince-dashboard/layouts/
  - zellij-setup/configs/
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update all Zellij KDL layout files that reference `claude-sandbox` as a command name.

**Why**: KDL layouts specify the command to run in panes. After the rename, they must use `agent-sandbox`.

**Implementation plan**:
1. Search all `.kdl` files: `grep -r \"claude-sandbox\" --include=\"*.kdl\"`
2. Replace `command \"claude-sandbox\"` → `command \"agent-sandbox\"` in each file
3. Files expected:
   - `lince-dashboard/layouts/agent-multi.kdl`
   - `lince-dashboard/layouts/agent-single.kdl` (if exists)
   - `zellij-setup/configs/three-pane.kdl`
   - `zellij-setup/configs/three-pane-mm.kdl`
   - `zellij-setup/configs/three-pane-vertex.kdl`
   - `zellij-setup/configs/three-pane-zai.kdl`
4. Verify layouts load correctly (visual check in Zellij or syntax validation)

**~9 reference changes across ~6 files. Mechanical find-and-replace.**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All command "claude-sandbox" replaced with command "agent-sandbox" in KDL files
- [x] #2 Zero remaining claude-sandbox references in any .kdl file
- [x] #3 Layouts are syntactically valid KDL
<!-- AC:END -->
