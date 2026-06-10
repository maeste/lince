---
id: LINCE-139
title: >-
  Docs rationalization: single-source documentation system aligned with Config
  v2
status: Done
assignee: []
created_date: '2026-06-09 21:04'
updated_date: '2026-06-10 10:31'
labels:
  - config-v2
  - documentation
milestone: m-16
dependencies:
  - LINCE-128
  - LINCE-130
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/212'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#212 (epic #200).

Documentation drift is a root cause of real bugs (#199 was docs-vs-update.sh-vs-skill; shipped config comments still claim [profiles.*] auto-discovery and nono-on-macOS; three overlapping skill doc payloads incl. orphaned lince-setup/lince_setup). Same cure as the config: one source of truth, the rest generated or explicitly derived. Scope: (1) config reference generated from the #203 schema (docs/, website, skill references/) with CI divergence check; (2) docs inventory with declared ownership (generated / hand-curated / delete), consolidating the three skill payloads into one; (3) one-time audit of shipped-file comments, which become template content under the LINCE-129 ownership contract; (4) coordination with LINCE-115 (CLI docs/website) to avoid double churn on the same files. Inventory/consolidation can start immediately; generation depends on the schema.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Config reference authored in exactly one place (the schema) and generated everywhere else; CI fails on divergence
- [ ] #2 Docs inventory table committed (surface -> owner -> generated|curated|deleted); three skill payloads collapsed to one, orphaned lince-setup payload removed
- [ ] #3 No shipped config file carries a comment contradicting current behavior
- [ ] #4 Coordination note agreed with LINCE-115 on website/docs sequencing
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Remainder merged via PR https://github.com/RisorseArtificiali/lince/pull/230 (Closes #212; the inventory half had landed earlier). lince-config schemas enriched with per-key description/default; scripts/gen_config_reference.py generates the skill's sandbox-config.md/dashboard-config.md and docs/documentation/configuration-keys.md (all five schemas, in sidebar); scripts/tests/test_config_reference.py is the divergence check (incl. no-description-holes). Ubuntu 24.04+ AppArmor prerequisite note added to QUICKSTART.md and sandbox/README.md.
<!-- SECTION:FINAL_SUMMARY:END -->
