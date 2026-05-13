---
id: LINCE-120
title: Initial state Unknown + pane discovery refactor
status: Done
assignee: []
created_date: '2026-05-13 20:00'
updated_date: '2026-05-13 20:40'
labels: []
milestone: m-15
dependencies:
  - LINCE-118
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/116'
  - lince-dashboard/plugin/src/agent.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Sostituisci il marker di "agente in attesa di pane" da `AgentStatus::Starting` a `pane_id.is_none()`. Cambia lo stato iniziale di tutti gli agenti a `Unknown`.

**Changes**:

In `agent.rs`:
- Riga 515 (`spawn_agent` o equivalente): initial status `AgentStatus::Starting` → `AgentStatus::Unknown`.
- Riga 624: il loop di pane discovery oggi gira `else if agent.status == AgentStatus::Starting`. Cambia in `else if agent.pane_id.is_none() && !matches!(agent.status, AgentStatus::Stopped)`.
- Riga 651: quando la pane viene trovata, il comportamento dipende dal tipo di agente:
  - **Agente con hook nativi** (`has_native_hooks = true`): resta `Unknown`. Gli hook eventi lo guideranno (Claude emette `idle_prompt` quando il prompt diventa attivo → diventa `INPUT`).
  - **Agente senza hook nativi** (`has_native_hooks = false`): resta `Unknown` per sempre fino a `Stopped`. Coerente con il design.
  - In entrambi i casi: NON forzare la transizione a `WaitingForInput` come oggi.

**Verifica**: il test end-to-end con Claude deve confermare che dopo lo spawn l'agente passa da `Unknown` a `INPUT` non appena Claude inizializza il prompt. Se Claude NON emette un evento all'inizializzazione, vale la pena modificare `claude-status-hook.sh` per emettere `input` esplicitamente quando il prompt diventa attivo (es. dal `SessionStart` hook di Claude se esiste, oppure dal primo `idle_prompt`).

**Why**

Risolve l'altra parte di #116: oggi gli agenti senza hook mostrano "Running" dopo la pane discovery, ma sono semplicemente in attesa. Il nuovo modello li lascia `Unknown` onestamente.

**Edge case**: se un utente avvia un agente con hook nativi ma per qualche motivo l'hook non parte (es. script mancante), l'agente resterà `Unknown` per sempre. È accettabile e visivamente onesto.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Spawn di un nuovo agente lo crea con status `Unknown`
- [x] #2 Pane discovery non promuove più ad AgentStatus::WaitingForInput automaticamente; il comportamento post-discovery dipende dagli hook
- [x] #3 Agenti con `has_native_hooks=false` rimangono in `Unknown` fino allo stop
- [ ] #4 Agenti con `has_native_hooks=true` (Claude) raggiungono `INPUT` dopo la prima interazione effettiva, verificato manualmente
- [x] #5 Pane exit transita correttamente a `Stopped` (preservato dal flow esistente in agent.rs:609-622)
- [x] #6 Nessun riferimento residuo a AgentStatus::Starting
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Wave 2B sequential after LINCE-119. Delegated to subagent. Initial state Unknown (already partially done by LINCE-118 swap); the actual scope is changing the pane discovery predicate from status-based to pane_id-based.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Subagent (refactoring-expert) execution. agentId: aef7104938adc38ee. Build verified by orchestrator post-completion.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Pane discovery refactored. agent.rs:623 predicate changed from `agent.status == AgentStatus::Unknown` to `agent.pane_id.is_none() && !matches!(agent.status, AgentStatus::Stopped)` — decoupling discovery from status. The auto-promotion to WaitingForInput after a pane match is removed (replaced with an explanatory comment): for native-hook agents the hook events drive transitions; for non-hook agents the dashboard stays Unknown for the entire lifetime, which is the intended honest behavior. Initial spawn status is Unknown (LINCE-118 mechanical swap). Pane-exit detection in agent.rs:609-622 preserved (transitions to Stopped). Restarted agents (pane_id=None, status!=Stopped) are picked up correctly by the new predicate. Build clean: 0 warnings, 0 errors. Zero residual AgentStatus::Starting references. AC4 (Claude reaches INPUT after first interaction) requires live verification — deferred to LINCE-123.
<!-- SECTION:FINAL_SUMMARY:END -->
