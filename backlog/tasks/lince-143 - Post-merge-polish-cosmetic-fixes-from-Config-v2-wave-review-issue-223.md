---
id: LINCE-143
title: 'Post-merge polish: cosmetic fixes from Config-v2 wave review (issue #223)'
status: Done
assignee: []
created_date: '2026-06-10 12:36'
updated_date: '2026-06-10 12:46'
labels:
  - polish
  - docs
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Batch of cosmetic / doc / test-hygiene fixes from the adversarial review of Config v2 wave (PRs #214–#220), tracked upstream as https://github.com/RisorseArtificiali/lince/issues/223.\n\nAreas: sandbox proxy-rule warning text, seatbelt docs/test hygiene, install.sh .bak timestamp unification, docs-inventory sidebar + citations, MULTI-AGENT-GUIDE prose, landlock spike README, config-v2 design doc §3.5/§4.3/registry-transition notes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All checklist items from issue #223 addressed or explicitly noted as not-fixable (e.g. historical commit subjects)
- [x] #2 PR opened against RisorseArtificiali/lince with Closes #223
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
PR https://github.com/RisorseArtificiali/lince/pull/240 (Closes #223). All issue items addressed except: sidebar link + docs/README.md inventory row (already fixed by b4fc8a29/#212) and the two >72-char landlock spike commit subjects (merged history, not amendable). Validation: agent-sandbox --help OK, test-seatbelt-profile-network.sh and test-credential-proxy.sh (40 assertions) pass.
<!-- SECTION:FINAL_SUMMARY:END -->
