---
id: LINCE-135
title: >-
  Discovery helpers: detect installed agents/toolchains/paths and propose policy
  entries
status: To Do
assignee: []
created_date: '2026-06-09 20:52'
labels:
  - guided-config
milestone: m-17
dependencies:
  - LINCE-134
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/208'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#208 (epic #206). Inspired by mxc SDK discovery helpers.

`lince config discover`: detect installed agent binaries, relevant toolchains on PATH, candidate rw/ro paths; emit ready-made apply suggestions (human output + --json for skill/wizard). Fixes the #125 relative-path class (absolute validated paths only) and enables quickstart to stop hardcoding the agent list (#41).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With claude+codex installed, discover proposes exactly those two agent templates with valid absolute paths
- [ ] #2 Applied suggestions always pass lince config validate
<!-- AC:END -->
