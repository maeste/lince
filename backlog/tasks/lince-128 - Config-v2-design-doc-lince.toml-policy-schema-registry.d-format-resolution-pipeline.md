---
id: LINCE-128
title: >-
  Config v2 design doc: lince.toml policy schema, registry.d format, resolution
  pipeline
status: To Do
assignee: []
created_date: '2026-06-09 20:51'
updated_date: '2026-06-09 20:53'
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
