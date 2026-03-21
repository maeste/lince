---
id: LINCE-51
title: Support hot-reloading config.toml without plugin restart
status: Done
assignee: []
created_date: '2026-03-19 10:41'
updated_date: '2026-03-20 08:58'
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
- [x] #1 Config changes detected within 5 seconds
- [x] #2 Safe settings applied to running state
- [x] #3 Notification shown on reload
- [x] #4 Parse errors shown without crash
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented config hot-reload via timer-based mtime checking (5s interval). Added config_path/config_mtime to State, get_file_mtime() helper, reload_config() method that selectively applies safe fields (focus_mode, status_method, max_agents, templates, etc.) while preserving sandbox_command. Parse errors preserve old config. Hot-reloadable settings documented in README.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Manual test: change focus_mode in config.toml, verify applied within 5 seconds
- [x] #2 Hot-reloadable settings documented in README
<!-- DOD:END -->
