---
id: LINCE-134
title: >-
  Template composition: lince config apply <agent>+<level>+<provider> with
  shipped preset bricks
status: To Do
assignee: []
created_date: '2026-06-09 20:52'
labels:
  - guided-config
milestone: m-17
dependencies:
  - LINCE-130
  - LINCE-131
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/207'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#207 (epic #206).

Composition engine over the Config v2 policy layer: schema-validated bricks (agent from registry.d, isolation level, provider, optional project preset) composed by `lince config apply claude+normal+anthropic` into lince.toml policy entries. LINCE-106 extends-inheritance is the merge precedent. Includes `lince config templates` listing, idempotent re-apply, --dry-run diff, and replacing quickstart's selection logic with apply calls.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Fresh machine reaches working sandboxed-Claude setup with one apply command
- [ ] #2 Re-running apply is a no-op
- [ ] #3 Invalid combination fails with a clear message before writing anything
<!-- AC:END -->
