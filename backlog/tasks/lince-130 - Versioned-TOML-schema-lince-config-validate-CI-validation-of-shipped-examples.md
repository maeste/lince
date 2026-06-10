---
id: LINCE-130
title: >-
  Versioned TOML schema + lince config validate + CI validation of shipped
  examples
status: Done
assignee: []
created_date: '2026-06-09 20:52'
updated_date: '2026-06-10 09:36'
labels:
  - config-v2
milestone: m-16
dependencies:
  - LINCE-128
  - LINCE-107
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/203'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#203 (epic #200).

Publish a JSON Schema for lince.toml and registry.d/*.toml (Taplo-compatible for editor support). Implement `lince config validate` with schema + version-contract checks (dual-read window, explicit older/newer-than-supported errors), replacing the hand-written drifting SANDBOX_SCHEMA/DASHBOARD_SCHEMA dicts in lince-config. Add a CI job validating every shipped example/template config. Structural fix for the #197 stale-config class.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 lince config validate catches unknown/missing keys and stale version with actionable messages
- [ ] #2 CI fails when a shipped example violates the schema
- [ ] #3 Hand-written schema dicts in lince-config removed
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Merged via PR https://github.com/RisorseArtificiali/lince/pull/225 (Closes #203). Published Taplo-compatible JSON Schemas (schemas/*.schema.json) for lince.toml v2, registry.d agent/provider files, and the legacy v1 sandbox/dashboard configs; lince-config validate is now schema-driven (replaces hand-written dicts) with the §2.1 version contract (dual-read window, fail-closed older/newer, fixing command named); new targets lince/registry + --file/--overlay; `lince-config schema` emits the schemas; scripts/tests/test_schemas.py validates every shipped example with zero errors/warnings (17 tests).
<!-- SECTION:FINAL_SUMMARY:END -->
