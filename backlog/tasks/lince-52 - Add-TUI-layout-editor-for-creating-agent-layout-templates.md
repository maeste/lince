---
id: LINCE-52
title: Add TUI layout editor for creating agent layout templates
status: To Do
assignee: []
created_date: '2026-03-19 10:41'
updated_date: '2026-03-19 10:45'
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
- [ ] #1 l key opens layout editor mode
- [ ] #2 Can view, create, and edit layout templates
- [ ] #3 Changes saved to config.toml
- [ ] #4 ASCII preview of layout structure
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Create and save a new template via TUI, verify usable for spawning agents
<!-- DOD:END -->
