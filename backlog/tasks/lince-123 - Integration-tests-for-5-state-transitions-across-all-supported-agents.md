---
id: LINCE-123
title: Integration tests for 5-state transitions across all supported agents
status: To Do
assignee: []
created_date: '2026-05-13 20:01'
labels: []
milestone: m-15
dependencies:
  - LINCE-119
  - LINCE-120
  - LINCE-121
  - LINCE-122
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/116'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

End-to-end validation che il 5-state model funzioni per tutti gli agenti supportati.

**Test scenarios**:

**1. Non-hook agents (bash, fish, zsh, gemini)**
- Spawn → stato `Unknown` (label "-")
- Resta `Unknown` per tutta la sessione
- Chiudi pane → `Stopped` con eventuale exit_code
- `needs_attention` flag NON deve mai essere true (no INPUT/PERMISSION)

**2. Claude (hook nativi)**
- Spawn → `Unknown`
- Dopo init del prompt → `INPUT` (via event_map idle_prompt → input)
- Invio prompt e tool use → `Running` (via PreToolUse → running)
- Approvazione richiesta → `PERMISSION` (via permission_prompt → permission)
- Fine turno → `INPUT` (di nuovo)
- Stop o exit → `Stopped`
- Le 4 transizioni emettono correttamente `needs_attention=true` su INPUT/PERMISSION

**3. Codex (hook nativi)**
- Stesso pattern di Claude se i nomi eventi sono mappati correttamente. Se Codex non ha permission event, salta quello stato — coerente.

**4. Pi (hook TypeScript)**
- Spawn → `Unknown`
- session_start → mapping configurato (probabilmente `input` o `running`)
- tool_call → `Running`
- turn_end → `INPUT`
- session_shutdown → `Stopped`

**5. Restore from save state**
- Salva con `/save-and-quit`
- Riavvia dashboard
- Tutti gli agenti non-Stopped vengono ripristinati con stato iniziale `Unknown` (no stato persistente preservato)
- File di save vecchi (con `tokens_in` ecc.) non causano panic — vengono caricati con i campi rimossi ignorati

**6. Unknown event handling**
- Hook che emette un evento sconosciuto (es. typo) → status diventa `Unknown` con log warning, NON `Running` silenzioso

**Strumenti di verifica**:
- Unit test in `types.rs` per ogni branch di `to_agent_status()` e `canonical_status()`
- Test manuale guidato: documento step-by-step con screenshot/note nel PR
- Se esiste infrastruttura di integration test per il plugin WASM, integrarla; altrimenti documentare la procedura di test manuale

**Why**

Senza validazione end-to-end, il refactor può introdurre regressioni invisibili (es. Claude perde lo stato PERMISSION). Risolve #116 quando tutti i casi sono coperti.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bash/gemini/zsh/fish mostrano '-' per tutta la sessione (no falsi 'Running')
- [ ] #2 Claude transita correttamente attraverso tutti i 5 stati (Unknown→INPUT→Running→PERMISSION→INPUT→Stopped)
- [ ] #3 Codex transita correttamente tra gli stati attesi
- [ ] #4 Pi transita correttamente
- [ ] #5 `needs_attention` evidenziato in tabella solo per INPUT/PERMISSION
- [ ] #6 File di save legacy si caricano senza crash (campi extra ignorati)
- [ ] #7 Evento hook sconosciuto → status Unknown + log warning, non Running
<!-- AC:END -->
