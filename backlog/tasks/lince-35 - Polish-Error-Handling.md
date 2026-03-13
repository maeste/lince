---
id: LINCE-35
title: Polish + Error Handling
status: Done
assignee: []
created_date: '2026-03-10 14:16'
updated_date: '2026-03-10 20:39'
labels:
  - voxtts
  - polish
  - error-handling
milestone: m-9
dependencies:
  - LINCE-31
  - LINCE-32
  - LINCE-33
  - LINCE-34
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Final polish pass: graceful error handling, help commands, config documentation, linting.

CUDA not available → warning + automatic CPU fallback.
Kokoro not installed → clear error suggesting alternative engine.
Missing clipboard tools → clear error message.
--list-voices and --list-devices commands.
All linting passes (ruff, line length 119).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CUDA not available → warning + automatic CPU fallback
- [ ] #2 Kokoro not installed → clear error suggesting alternative engine
- [ ] #3 Missing clipboard tools → clear error message
- [ ] #4 --list-voices shows available voices for selected engine
- [ ] #5 --list-devices shows audio output devices
- [ ] #6 config.example.toml complete and documented
- [ ] #7 All linting passes (ruff, line length 119)
<!-- AC:END -->
