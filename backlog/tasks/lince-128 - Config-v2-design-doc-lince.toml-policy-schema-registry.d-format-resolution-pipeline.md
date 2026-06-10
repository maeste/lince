---
id: LINCE-128
title: >-
  Config v2 design doc: lince.toml policy schema, registry.d format, resolution
  pipeline
status: Done
assignee: []
created_date: '2026-06-09 20:51'
updated_date: '2026-06-10 12:23'
labels:
  - config-v2
  - design
milestone: m-16
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/201'
  - 'https://github.com/RisorseArtificiali/lince/issues/200'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#201 (epic #200).

Lock the Config v2 contracts before code moves: lince.toml policy schema (version field, [network] default-deny, [agents.*], project overlay per LINCE-105 precedent), registry.d/ one-file-per-agent format (union of both agents-defaults.toml schemas), resolution pipeline (layering order, generated outputs, dual-read migration window for existing installs), and the naming cleanup retiring the triple meaning of "profile".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Design doc in docs/ with worked example configs
- [ ] #2 Every key consumed by resolve_agent_config (sandbox) and parse_agent_defaults (dashboard) has a defined home in the new schema
- [ ] #3 Dual-read migration policy for legacy ~/.agent-sandbox/config.toml and dashboard config is specified
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Config v2 design doc shipped to main as docs/design/config-v2-design.md (issue #201, PR #219, pre-session). The lince.toml policy schema, registry.d format, resolution pipeline, resolve --json shape, dual-read migration and the design invariants (I1-I7) are all implemented across the wave-2 PRs (#224-#236, #238). Stale backlog status corrected post-wave.
<!-- SECTION:FINAL_SUMMARY:END -->
