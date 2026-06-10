---
id: LINCE-134
title: >-
  Template composition: lince config apply <agent>+<level>+<provider> with
  shipped preset bricks
status: Done
assignee: []
created_date: '2026-06-09 20:52'
updated_date: '2026-06-10 10:38'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Merged via PR https://github.com/RisorseArtificiali/lince/pull/231 (Closes #207). lince-config apply <agent>[+<level>][+<provider>] composes registry/level/provider bricks into lince.toml (validate-before-write, idempotent, --dry-run diff, --project overlay, §5.2 v2-switch guard with --force-v2); lince-config templates lists bricks (--json for the wizard); --target lince on the editing commands; resolve honors [dashboard].enabled_agents; quickstart's awk-filtered agents-defaults rewrites replaced by apply + enabled_agents. 14 new tests.
<!-- SECTION:FINAL_SUMMARY:END -->
