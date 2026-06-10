---
id: LINCE-141
title: >-
  Effective-policy attestation record: per-launch requested-vs-enforced boundary
  + dashboard badge
status: To Do
assignee: []
created_date: '2026-06-10 07:48'
labels:
  - config-v2
  - security
milestone: m-16
dependencies:
  - LINCE-132
  - LINCE-138
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/221'
  - >-
    https://github.com/RisorseArtificiali/lince/issues/211#issuecomment-4664876502
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#221 (epic #200). From rpelevin's feedback on the Landlock spike (#211 comment).

agent-sandbox emits a per-launch effective-policy JSON record (backend, requested level/fs/net refs, Landlock ABI, fs/net enforced flags, net limitation port-only|host-unaware|unavailable, bwrap args digest, helper digest, applied-before-exec, inheritance verified, degraded_reason). Fail-closed contract: paranoid never degrades silently (same philosophy as the #196 Seatbelt guard); degraded operation only as explicit opt-in with the missing boundary named in the record. Dashboard surfaces the enforced boundary per agent (badge/column) — resolve --json is the REQUESTED view, this record is the ENFORCED view.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every sandbox launch writes an effective-policy record consumable by the dashboard
- [ ] #2 paranoid fails closed when the requested fs boundary cannot be enforced; degraded mode is explicit and recorded with the exact missing boundary
- [ ] #3 Dashboard shows the enforced boundary per agent (badge/column fed by the record)
- [ ] #4 Record fields match the #221 schema incl. net limitation and digests
<!-- AC:END -->
