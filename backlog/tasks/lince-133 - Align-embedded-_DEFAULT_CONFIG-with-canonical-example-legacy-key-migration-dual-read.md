---
id: LINCE-133
title: >-
  Align embedded _DEFAULT_CONFIG with canonical example + legacy-key migration
  (dual-read)
status: Done
assignee: []
created_date: '2026-06-09 20:52'
updated_date: '2026-06-10 09:58'
labels:
  - config-v2
milestone: m-16
dependencies:
  - LINCE-128
  - LINCE-130
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/205'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub: RisorseArtificiali/lince#205 (epic #200).

Single-source the default config: embedded _DEFAULT_CONFIG (agent-sandbox:57-200) and sandbox/config.toml.example must be the same artifact (build-time include or equality test). Fresh init writes canonical default_provider/[providers.*] (today it writes legacy spelling and immediately triggers the deprecation warning). Extend migrate-providers to v2 renames per the dual-read policy, then schedule removal of legacy aliases in Python (agent-sandbox:1394) and Rust (config.rs:264).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Fresh init passes lince config validate with zero deprecation warnings
- [ ] #2 Test fails if embedded default and shipped example diverge
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Merged via PR https://github.com/RisorseArtificiali/lince/pull/227 (Closes #205). _DEFAULT_CONFIG and sandbox/config.toml.example are now byte-identical (canonical default_provider/[providers.*] spelling; example gains [sandbox].backend); fresh init is warning-free and passes lince-config validate with zero issues; scripts/tests/test_default_config.py guards equality. migrate-providers already covers the default_profile/[profiles.*] renames; v2 renames land with lince config migrate.
<!-- SECTION:FINAL_SUMMARY:END -->
