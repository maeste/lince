---
id: LINCE-47
title: Add interactive TUI wizard for creating agents with custom settings
status: To Do
assignee: []
created_date: '2026-03-19 10:40'
updated_date: '2026-03-19 10:45'
labels:
  - dashboard
  - tui
  - enhancement
milestone: m-11
dependencies:
  - LINCE-39
  - LINCE-40
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace "press n to spawn with defaults" with an interactive multi-step wizard in the dashboard TUI.

## Implementation Plan

1. Add `WizardState` enum to `types.rs`: `Inactive`, `Step1Name(String)`, `Step2Profile(Vec<String>, usize)`, `Step3Dir(String)`, `Step4Layout(AgentLayout)`, `Confirm`
2. In `dashboard.rs`: add `render_wizard()` that overlays wizard steps on dashboard area
3. In `update()`: when wizard active, route key events to wizard state machine (text input for name/dir, list selection for profile/layout)
4. On confirm: `spawn_agent()` with wizard values, reset wizard state
5. On `Escape`: cancel wizard, return to dashboard
6. Back-navigation between steps with Shift+Tab or Backspace
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 n key opens multi-step wizard overlay
- [ ] #2 Each step accepts appropriate input (text/selection)
- [ ] #3 Escape cancels, Enter advances/confirms
- [ ] #4 Agent spawned with user-provided settings
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All 4 wizard steps functional
- [ ] #2 Back-navigation between steps works
- [ ] #3 Manual test: complete wizard, verify agent spawned with correct settings
<!-- DOD:END -->
