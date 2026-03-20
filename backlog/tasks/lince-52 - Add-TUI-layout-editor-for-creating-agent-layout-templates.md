---
id: LINCE-52
title: Add TUI layout editor for creating agent layout templates
status: Done
assignee: []
created_date: '2026-03-19 10:41'
updated_date: '2026-03-19 21:51'
labels:
  - dashboard
  - tui
  - enhancement
milestone: m-11
dependencies:
  - LINCE-45
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Simplified way to create and edit agent layout templates from within the TUI dashboard.

## Implementation Plan

1. Add layout editor mode: `l` key opens editor
2. Show list of existing layout templates (from config.toml `[templates]` or layout files)
3. Allow creating new templates: name, pane count, pane commands
4. Save to config.toml `[templates]` section
5. Preview layout structure as ASCII art before saving
6. Edit existing templates: modify pane commands, resize ratios
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 l key opens layout editor mode
- [x] #2 Can view, create, and edit layout templates
- [x] #3 Changes saved to config.toml
- [x] #4 ASCII preview of layout structure
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added layout editor mode via 'l' key with LayoutEditorState/LayoutEditorMode/LayoutCreateState types. Supports List mode (browse/delete), Create flow (Name → PaneCount → PaneConfig → Preview), ASCII art preview for 2/3/4-pane layouts with box-drawing characters. Layouts saved in session memory. Compiles cleanly.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Create and save a new template via TUI, verify usable for spawning agents
<!-- DOD:END -->
