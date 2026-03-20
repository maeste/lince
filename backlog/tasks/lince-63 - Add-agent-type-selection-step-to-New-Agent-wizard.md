---
id: LINCE-63
title: Add agent type selection step to New Agent wizard
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
labels:
  - dashboard
  - wizard
  - UX
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-59
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/dashboard.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The wizard currently has steps: Name → Profile → ProjectDir → Confirm. Add a new first step "AgentType" showing configured agent types. Non-Claude types skip the Profile step (profiles are sandbox-specific). Quick-create (`n` key) defaults to "claude".

**Why**: Users need a way to select which agent type to spawn. The wizard is the primary UI for creating agents with custom settings.

**Key files**: `plugin/src/types.rs` (WizardState, WizardStep), `plugin/src/main.rs` (wizard event handling), `plugin/src/dashboard.rs` (wizard rendering)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 WizardStep::AgentType variant exists as first step
- [ ] #2 Wizard shows list of configured agent types when N is pressed
- [ ] #3 Non-Claude types skip the Profile step
- [ ] #4 Quick-create (n key) defaults to Claude sandboxed agent type
- [ ] #5 Wizard confirm screen displays the selected agent type
- [ ] #6 Selected agent type passed through to spawn_wizard_agent()
<!-- AC:END -->
