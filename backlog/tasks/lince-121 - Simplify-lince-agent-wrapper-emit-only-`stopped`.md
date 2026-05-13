---
id: LINCE-121
title: 'Simplify lince-agent-wrapper: emit only `stopped`'
status: Done
assignee: []
created_date: '2026-05-13 20:00'
updated_date: '2026-05-13 20:28'
labels: []
milestone: m-15
dependencies: []
references:
  - lince-dashboard/hooks/lince-agent-wrapper
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

`lince-dashboard/hooks/lince-agent-wrapper` oggi emette `start` all'avvio e `stopped` all'uscita. Drop l'evento `start` — emetti solo `stopped`.

**Why**

Con il nuovo modello, agenti senza hook nativi devono restare `Unknown` fino allo stop. Il `start` event:
- Oggi mappa a `Running` (sbagliato per non-hook agents, source di #116)
- Domani sarebbe mappato a `Unknown` (no-op rispetto allo stato iniziale)

Quindi è inutile: rimuoverlo elimina rumore sul pipe e semplifica.

**Fallback file-based** (`/tmp/lince-dashboard/<agent_id>.state`):
- Drop la scrittura della state file all'avvio
- Mantieni la scrittura all'exit con `event: "stopped"`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Wrapper non emette più il JSON `{event: "start"}` al lancio
- [x] #2 Wrapper emette `{event: "stopped", exit_code: N}` all'uscita (mantenendo l'exit code)
- [x] #3 Fallback file `/tmp/lince-dashboard/<id>.state` non contiene più stato iniziale `start`
- [ ] #4 Test manuale: bash agent spawnato via wrapper resta in `-` (Unknown) finché non viene chiuso, poi `Stopped`
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation delegated to subagent. Plan = description in task body. Isolated change in hooks/lince-agent-wrapper.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Subagent (general claude) execution. agentId: a65b8bf18e22da8cb. AC4 (manual test bash agent → Unknown until exit) deferred to integration tests in LINCE-123.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Wrapper at lince-dashboard/hooks/lince-agent-wrapper reduced to 71 lines (was 75). Startup `send_event "start"` removed; only the exit-trap `send_event "stopped"` with exit_code remains. Header comment updated. set -uo pipefail, arg parsing, HAS_ZELLIJ detection, send_event() helper (pipe + file fallback), trap cleanup EXIT, and exec "$@" all preserved. Smoke run with /bin/true: exits 0, no startup emission, state file contains only `stopped`, debug log shows single event. Manual e2e test in real dashboard deferred to LINCE-123.
<!-- SECTION:FINAL_SUMMARY:END -->
