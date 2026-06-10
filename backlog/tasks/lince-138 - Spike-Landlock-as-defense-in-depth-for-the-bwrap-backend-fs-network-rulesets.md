---
id: LINCE-138
title: >-
  Spike: Landlock as defense-in-depth for the bwrap backend (fs + network
  rulesets)
status: Done
assignee: []
created_date: '2026-06-09 21:01'
updated_date: '2026-06-10 12:23'
labels:
  - spike
  - security
milestone: m-16
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/211'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#211.

Evaluate Landlock as a hardening layer inside the existing bubblewrap backend (NOT a new backend): ruleset applied before exec adds a kernel-enforced second fence on fs and, on ABI v4 (kernel >=6.7), TCP bind/connect. Linux twin of #196 (paranoid must actually contain). Prior art: Codex CLI (landlock+seccomp), landrun/nsjail; mxc does NOT use it. Spike questions: ABI matrix on target distros, application point in agent-sandbox (inheritance across subprocesses), port-based net rules vs credential proxy / future allowed_hosts, ordering with bwrap binds, spawn overhead. Findings feed the [filesystem]/[network] policy keys in the Config v2 design doc (LINCE-128) so the same intent compiles to bind mounts AND Landlock.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Feasibility doc with ABI availability matrix and enforcement-per-ABI recommendation
- [ ] #2 Prototype branch: one agent at paranoid gated by Landlock fs rules (+ net if kernel allows)
- [ ] #3 Recommendation on default-on levels and required [filesystem]/[network] policy keys delivered as input to LINCE-128
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Landlock defense-in-depth spike completed (issue #211 / PR #218, pre-session; verdict GO, docs/design/landlock-spike.md). The spike's recommendation was implemented in wave-2 #222 (PR #229): __landlock-exec folded into agent-sandbox with the spike's level defaults, fail-closed at paranoid, and the gate ported to sandbox/tests/test-landlock-exec.sh. Stale backlog status corrected post-wave.
<!-- SECTION:FINAL_SUMMARY:END -->
