---
id: LINCE-142
title: >-
  Integrate Landlock enforcement into agent-sandbox (__landlock-exec) per spike
  GO
status: To Do
assignee: []
created_date: '2026-06-10 08:01'
labels:
  - security
  - sandbox
milestone: m-16
dependencies:
  - LINCE-138
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/222'
  - 'https://github.com/RisorseArtificiali/lince/issues/211'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#222. Follow-up of the #211 spike (LINCE-138, verdict GO). Hardening layer for the existing bwrap backend, NOT a second sandbox product.

Fold sandbox/spikes/landlock/landlock_exec.py into agent-sandbox as the __landlock-exec internal subcommand (last bwrap argv element — preexec_fn experimentally rejected). Defaults per spike: paranoid = fs+net(connect->8118 only), normal = fs+net-when-proxy-active, permissive = off. Fail-closed at paranoid (design invariant I7); emits its share of the effective-policy record (#221/LINCE-141). Config keys aligned with [filesystem]/[network] from the design doc (LINCE-128); interim level-based keying acceptable pre-v2. Port the gate assertions into sandbox/tests/.

Validation gates: re-run probe+demo+gate on Ubuntu 24.04 GA (ABI v4 floor — cited, not yet probed) and on a no-Landlock kernel (real boot, not just FORCE_ABI simulation).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 __landlock-exec subcommand applies fs(+net ABI>=4) ruleset inside the final mount namespace and execs the agent
- [ ] #2 paranoid fails closed when the fs boundary cannot be enforced, naming the missing boundary; degraded only as explicit opt-in
- [ ] #3 Level defaults match the spike recommendation (paranoid/normal/permissive)
- [ ] #4 sandbox/tests/ check ported from the spike gate
- [ ] #5 Validated on Ubuntu 24.04 GA ABI v4 and on a no-Landlock kernel path
<!-- AC:END -->
