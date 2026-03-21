---
id: LINCE-47
title: Add interactive TUI wizard for creating agents with custom settings
status: Done
assignee: []
created_date: '2026-03-19 10:40'
updated_date: '2026-03-19 21:51'
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
Add another key press "N" keeping the "press n to spawn with defaults". The capital letter N create a new agent with an interactive multi-step wizard in the dashboard TUI.

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
- [x] #1 n key opens multi-step wizard overlay
- [x] #2 Each step accepts appropriate input (text/selection)
- [x] #3 Escape cancels, Enter advances/confirms
- [x] #4 Agent spawned with user-provided settings
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented interactive TUI wizard activated via Shift+N. Added WizardState/WizardStep types, 4-step wizard flow (Name → Profile → ProjectDir → Confirm), centered overlay rendering with ANSI box drawing, back-navigation via Backspace, and spawn_agent_custom() for wizard-specified settings. Compiles cleanly.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All 4 wizard steps functional
- [x] #2 Back-navigation between steps works
- [x] #3 Manual test: complete wizard, verify agent spawned with correct settings
<!-- DOD:END -->
