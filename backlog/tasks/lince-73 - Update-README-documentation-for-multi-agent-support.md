---
id: LINCE-73
title: Update README documentation for multi-agent support
status: To Do
assignee: []
created_date: '2026-03-20 17:44'
labels:
  - documentation
milestone: m-12
dependencies:
  - LINCE-68
  - LINCE-69
  - LINCE-70
  - LINCE-71
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
- [ ] #1 README documents all supported agent types with config examples
- [ ] #2 Explains bwrap conflict handling per agent
- [ ] #3 Includes security warning for unsandboxed mode
- [ ] #4 Explains hook/wrapper system for status reporting
- [ ] #5 Shows example config.toml with agent type sections
<!-- AC:END -->
