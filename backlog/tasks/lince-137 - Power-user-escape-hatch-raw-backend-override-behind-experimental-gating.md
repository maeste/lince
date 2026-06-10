---
id: LINCE-137
title: 'Power-user escape hatch: raw backend override behind experimental gating'
status: To Do
assignee: []
created_date: '2026-06-09 20:53'
labels:
  - guided-config
milestone: m-17
dependencies:
  - LINCE-128
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/210'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#210 (epic #206). Inspired by mxc seatbelt.profileOverride + stable/dev schema split.

[experimental] section in lince.toml with raw override valves (extra bwrap args, raw Seatbelt snippet per agent/level). Overrides are appended last, survive updates (user-owned file), flagged by validate (warn, not block), and reported by resolve --json so the dashboard can badge custom-policy agents.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Expert can add one bwrap bind or one Seatbelt rule without forking templates
- [ ] #2 validate flags the config as policy-overridden
- [ ] #3 Guided flows never surface experimental keys
<!-- AC:END -->
