---
id: LINCE-51
title: Support hot-reloading config.toml without plugin restart
status: To Do
assignee: []
created_date: '2026-03-19 10:41'
updated_date: '2026-03-19 10:45'
labels:
  - dashboard
  - config
  - enhancement
milestone: m-11
dependencies:
  - LINCE-38
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Detect config.toml changes and apply them to the running plugin without restart.

## Implementation Plan

1. Store config file mtime in State
2. On timer (every 5 seconds): check mtime via `std::fs::metadata()`
3. If changed: re-parse config, apply safe fields (focus_mode, status_method, max_agents)
4. Unsafe fields (sandbox_command) only apply to new agents, not running ones
5. Show notification "Config reloaded" in command bar for 3 seconds
6. On parse error: show error message, keep old config
7. Document which settings are hot-reloadable in README
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Config changes detected within 5 seconds
- [ ] #2 Safe settings applied to running state
- [ ] #3 Notification shown on reload
- [ ] #4 Parse errors shown without crash
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Manual test: change focus_mode in config.toml, verify applied within 5 seconds
- [ ] #2 Hot-reloadable settings documented in README
<!-- DOD:END -->
