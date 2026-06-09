---
id: LINCE-140
title: 'Config v2 migration guides: users + developers (clear, schematic, minimal)'
status: To Do
assignee: []
created_date: '2026-06-09 21:06'
labels:
  - config-v2
  - documentation
milestone: m-16
dependencies:
  - LINCE-131
  - LINCE-133
  - LINCE-139
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/213'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#213 (epic #200). Closing deliverable of m-16, shipped with the first v2 release.

Two documents, two audiences, same style constraints: schematic (tables/checklists over prose), as short as possible, "what do I do" not "why" (the why lives in the design doc, linked once).

1. docs/migration-v2-users.md — what happens automatically (dual-read, lince update migration, custom-agent import), manual steps as a legacy→new table, verification via lince config validate / resolve --json, rollback (.bak locations, version pinning), deprecation timeline.

2. docs/migration-v2-developers.md — new contracts at a glance (lince.toml / registry.d / generated outputs / resolve --json as the only read API), adding an agent before→after, removal schedule for legacy aliases and dashboard TOML parsing, schema-first rules for new keys (default-deny, version bump), skill-author rules (only apply/set/validate).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both docs exist, follow the LINCE-139 ownership model, and are linked from README + website + lince update output
- [ ] #2 A pre-v2 user can migrate following only the user guide, with no other doc
- [ ] #3 Style: tables/checklists, no section longer than ~10 lines of prose
<!-- AC:END -->
