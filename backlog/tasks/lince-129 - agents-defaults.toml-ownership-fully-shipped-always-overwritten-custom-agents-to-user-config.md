---
id: LINCE-129
title: >-
  agents-defaults.toml ownership: fully shipped + always overwritten, custom
  agents to user config
status: Done
assignee: []
created_date: '2026-06-09 20:52'
updated_date: '2026-06-10 12:23'
labels:
  - config-v2
milestone: m-16
dependencies:
  - LINCE-128
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/199'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#199 (epic #200).

Resolve the three-way ownership conflict (docs say overwritten, update.sh preserves, skill writes into it). Decision: shipped data, always overwritten on update; all custom agents move to user config [agents.*] (per-key override). Includes update.sh/install.sh changes, lince-add-supported-agent retarget, one-time migration note for users with custom agents in the file. This contract carries into registry.d/ (LINCE-131 dir.).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 update.sh always overwrites agents-defaults.toml from the shipped copy
- [ ] #2 lince-add-supported-agent writes custom dashboard agents to config.toml [agents.*]
- [ ] #3 Per-key (not full-entry) override semantics for user [agents.*] sections
- [ ] #4 Migration note for users who customized agents-defaults.toml
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
agents-defaults ownership contract (shipped = always overwritten, custom agents to user config) shipped to main via issue #199 / PR #216 (pre-session). Wave-2 #204 (registry.d) and #202 (resolve --json) realized the contract: registry.d is shipped/always-overwritten, custom agents live in lince.toml, the dashboard full-entry-replacement footgun is gone. Stale backlog status corrected post-wave.
<!-- SECTION:FINAL_SUMMARY:END -->
