---
id: LINCE-118
title: Collapse AgentStatus to 5 canonical states + simplify StatusMessage
status: To Do
assignee: []
created_date: '2026-05-13 20:00'
labels: []
milestone: m-15
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/116'
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/config.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Modifica `lince-dashboard/plugin/src/types.rs` e `main.rs` per ridurre `AgentStatus` a 5 stati canonici e ripulire `StatusMessage` dai campi rich.

**Changes**:

In `types.rs`:
- `AgentStatus` enum: drop `Starting`, `Idle`, `Error(String)`. Aggiungi `Unknown`. Stati finali: `Unknown`, `Running`, `WaitingForInput`, `PermissionRequired`, `Stopped`.
- `color()` / `label()`: aggiorna per i 5 stati. `Unknown` → dim gray `\x1b[90m` con label `"-"`.
- `canonical_status()`: accetta SOLO `"unknown"`, `"running"`, `"input"`, `"permission"`, `"stopped"`. Drop alias (`start`, `idle`, `waiting_for_input`, `permission_required`).
- `to_agent_status()`: drop il match hardcoded su nomi Claude (linee 93-97). Usa solo `event_map` per la traduzione. Fallback su evento sconosciuto: `Unknown` con log warning (oggi è `Running` silenzioso — questo è parte del fix #116).
- `StatusMessage` struct: drop `tokens_in`, `tokens_out`, `tool_name`, `model`. Resta `{agent_id, event, timestamp?, error?}`.

In `main.rs`:
- `handle_status` update (1276-1295): drop branch che popolano `tool_name`/`tokens`/`model`/`current_tool`.
- Drop branch `subagent_start` / `subagent_stop` (1264-1273).
- Drop branch `ignore_wrapper_start` (1255-1261).
- `apply_status_side_effects` call (1295): rimuovi se la funzione diventa vuota (vedi task LINCE-119).

In `config.rs`:
- `AgentTypeConfig`: drop campo `ignore_wrapper_start` (linee 54-58). Diventa dead.

**Why**

Foundation del 5-state model. Tutti gli altri task in m-15 dipendono da questo. Risolve la radice di #116 sul fallback silenzioso a `Running`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AgentStatus enum ha esattamente 5 varianti: Unknown, Running, WaitingForInput, PermissionRequired, Stopped
- [ ] #2 `canonical_status()` accetta solo i 5 nomi canonici lowercase
- [ ] #3 `to_agent_status()` con event_map vuoto e evento sconosciuto ritorna Unknown (con log warning), non Running
- [ ] #4 StatusMessage non ha più i campi tokens_in/out/tool_name/model
- [ ] #5 Compila senza warning, niente riferimenti residui a Starting/Idle/Error(_) o ai campi rimossi
- [ ] #6 Unit test coprono: canonical_status per ognuno dei 5 stati, to_agent_status con event_map custom, fallback Unknown su evento sconosciuto
- [ ] #7 ignore_wrapper_start rimosso da config.rs e main.rs
<!-- AC:END -->
