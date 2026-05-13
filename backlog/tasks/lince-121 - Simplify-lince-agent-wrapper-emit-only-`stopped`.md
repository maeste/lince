---
id: LINCE-121
title: 'Simplify lince-agent-wrapper: emit only `stopped`'
status: To Do
assignee: []
created_date: '2026-05-13 20:00'
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
- [ ] #1 Wrapper non emette più il JSON `{event: "start"}` al lancio
- [ ] #2 Wrapper emette `{event: "stopped", exit_code: N}` all'uscita (mantenendo l'exit code)
- [ ] #3 Fallback file `/tmp/lince-dashboard/<id>.state` non contiene più stato iniziale `start`
- [ ] #4 Test manuale: bash agent spawnato via wrapper resta in `-` (Unknown) finché non viene chiuso, poi `Stopped`
<!-- AC:END -->
