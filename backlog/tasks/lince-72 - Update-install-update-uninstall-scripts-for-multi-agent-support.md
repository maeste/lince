---
id: LINCE-72
title: Update install/update/uninstall scripts for multi-agent support
status: Done
assignee: []
created_date: '2026-03-20 17:44'
updated_date: '2026-03-25 07:06'
labels:
  - install
  - scripts
milestone: m-12
dependencies:
  - LINCE-65
  - LINCE-57
references:
  - lince-dashboard/install.sh
  - lince-dashboard/update.sh
  - lince-dashboard/uninstall.sh
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update install.sh, update.sh, and uninstall.sh to handle new artifacts: `lince-agent-wrapper` script, updated config.toml.example with agent type sections.

**Why**: Per project convention, all file copies and system modifications go through install scripts. New multi-agent files must be properly managed.

**Key files**: `lince-dashboard/install.sh`, `lince-dashboard/update.sh`, `lince-dashboard/uninstall.sh`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 install.sh installs lince-agent-wrapper to PATH-accessible location
- [x] #2 update.sh updates wrapper script
- [x] #3 uninstall.sh removes wrapper script
- [x] #4 config.toml.example includes agent type configuration examples
- [x] #5 Scripts remain idempotent and safe to run multiple times
<!-- AC:END -->
