---
id: LINCE-64
title: Show agent type indicator and unsandboxed warning in dashboard TUI
status: Done
assignee: []
created_date: '2026-03-20 17:43'
updated_date: '2026-03-25 06:56'
labels:
  - dashboard
  - TUI
  - rendering
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-58
references:
  - lince-dashboard/plugin/src/dashboard.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Show agent type indicator in dashboard TUI using `display_name`, `short_label`, and `color` from `AgentTypeConfig`. Show red warning for agents with `sandboxed: false`.

**Why**: Users need to visually distinguish agent types and be aware of unsandboxed agents. All rendering driven by config fields — no per-agent code branches.

**Implementation scope**:
- Agent table shows `short_label` column with configured `color`
- Detail panel shows `display_name`
- Agents with `sandboxed: false` get red warning indicator in both table and detail
- No hardcoded per-agent rendering logic

**Key file**: `plugin/src/dashboard.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Agent table shows short_label column with per-agent color from config
- [x] #2 Detail panel shows display_name from config
- [x] #3 Agents with sandboxed=false show red warning indicator
- [x] #4 Rendering is purely config-driven — no per-agent code branches
- [x] #5 User-defined agents render correctly using their config values
<!-- AC:END -->
