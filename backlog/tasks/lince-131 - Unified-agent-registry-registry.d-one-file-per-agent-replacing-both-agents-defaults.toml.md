---
id: LINCE-131
title: >-
  Unified agent registry (registry.d/): one file per agent replacing both
  agents-defaults.toml
status: To Do
assignee: []
created_date: '2026-06-09 20:52'
labels:
  - config-v2
milestone: m-16
dependencies:
  - LINCE-128
  - LINCE-129
  - LINCE-117
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/204'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#204 (epic #200).

One registry.d/<agent>.toml per shipped agent containing the union of sandbox keys (command, env, home dirs, scratch, bwrap_conflict…) and dashboard keys (command template, event_map, colors, providers, levels…). Kills the 4x Pi env-bundle duplication and per-variant event_map copies. Shipped = always overwritten (LINCE-129 contract); custom agents in lince.toml win per-key. Removes the double install location (~/.agent-sandbox + ~/.local/bin) and quickstart's awk-filtered rewrites — selection becomes data in lince.toml. One-time migration importing user additions from legacy files.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Adding a new agent = one registry file (+ optional hook), picked up by both sandbox and dashboard
- [ ] #2 Pi env bundle and event_maps defined exactly once
- [ ] #3 Update never loses a user's custom agent
- [ ] #4 quickstart awk rewrites removed
<!-- AC:END -->
