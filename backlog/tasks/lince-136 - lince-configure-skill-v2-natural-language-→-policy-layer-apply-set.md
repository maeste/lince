---
id: LINCE-136
title: 'lince-configure skill v2: natural language → policy-layer apply/set'
status: To Do
assignee: []
created_date: '2026-06-09 20:52'
labels:
  - guided-config
  - skill
milestone: m-17
dependencies:
  - LINCE-134
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/209'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#209 (epic #206). Supersedes the #101/LINCE-110 lince-config retarget — coordinate to avoid duplicate work.

Skill translates intents into lince config apply/set on lince.toml (never direct TOML edits, never mechanism keys), learns the template catalog via `lince config templates --json` and discovery output, validates after every change and reports the diff. references/ docs rewritten for the policy schema, keeping security guidance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Example intents produce correct validated lince.toml changes through CLI calls only
- [ ] #2 Skill refuses to write keys not in the schema
<!-- AC:END -->
