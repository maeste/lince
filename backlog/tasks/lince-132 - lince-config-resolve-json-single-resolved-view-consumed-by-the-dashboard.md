---
id: LINCE-132
title: 'lince config resolve --json: single resolved view consumed by the dashboard'
status: To Do
assignee: []
created_date: '2026-06-09 20:52'
labels:
  - config-v2
milestone: m-16
dependencies:
  - LINCE-128
  - LINCE-131
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/202'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#202 (epic #200).

Single-source config resolution: emit the fully-resolved view (agents with merged env/event_map/levels, provider names — never secret values, levels, backend) as JSON. Dashboard consumes it via run_command() and drops parse_providers_from_toml (config.rs:585), provider-file cat'ing (config.rs:671-697) and the three level-discovery globs (config.rs:713-753). Embedded event_map fallback (#198) stays as last-resort resilience. Eliminates the hand-synced Python<->Rust duplication.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Rust plugin no longer parses sandbox-owned TOML
- [ ] #2 One resolution implementation remains (Python/lince side)
- [ ] #3 Secrets never cross the JSON boundary
<!-- AC:END -->
