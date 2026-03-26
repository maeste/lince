---
id: LINCE-73
title: Update README documentation for multi-agent support
status: Done
assignee: []
created_date: '2026-03-20 17:44'
updated_date: '2026-03-25 07:06'
labels:
  - documentation
milestone: m-12
dependencies: []
references:
  - lince-dashboard/README.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update lince-dashboard/README.md and sandbox README with multi-agent configuration instructions, supported agents, bwrap conflict handling, and security warnings for unsandboxed mode.

**Why**: Users and contributors need documentation to configure and use multi-agent support.

**Key files**: `lince-dashboard/README.md`, `sandbox/README.md` (if exists)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README documents all supported agent types with config examples
- [x] #2 Explains bwrap conflict handling per agent
- [x] #3 Includes security warning for unsandboxed mode
- [x] #4 Explains hook/wrapper system for status reporting
- [x] #5 Shows example config.toml with agent type sections
<!-- AC:END -->
