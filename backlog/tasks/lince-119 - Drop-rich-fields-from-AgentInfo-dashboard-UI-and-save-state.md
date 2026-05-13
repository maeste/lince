---
id: LINCE-119
title: 'Drop rich fields from AgentInfo, dashboard UI, and save state'
status: To Do
assignee: []
created_date: '2026-05-13 20:00'
labels: []
milestone: m-15
dependencies:
  - LINCE-118
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/dashboard.rs
  - lince-dashboard/plugin/src/state_file.rs
  - lince-dashboard/plugin/src/agent.rs
  - lince-dashboard/plugin/src/main.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Rimuovi i campi rich da `AgentInfo`, dalla UI del dashboard e dal formato di save/restore. Niente backward compatibility — file di stato vecchi non saranno caricati e si rigenerano.

**Changes**:

In `types.rs`:
- `AgentInfo` struct: drop `tokens_in`, `tokens_out`, `current_tool`, `model`, `running_subagents` (linee 298-306).
- `SavedAgentInfo` struct: drop `tokens_in`, `tokens_out` (linee 360-361) + relativa logica in `From<&AgentInfo>` (382-383).
- `apply_status_side_effects()`: la funzione era housekeeping di `current_tool` e `running_subagents`. Diventa vuota → rimuovere il metodo e tutte le sue chiamate (main.rs:1295, 1370).
- `status_display()`: resta — gestisce solo `Stopped` con exit_code, non i rich fields.

In `dashboard.rs`:
- Drop `subagent_suffix` (446-450).
- Drop la riga "Tokens" del detail panel (655 — `format_tokens(agent.tokens_in)` ecc.).
- Drop la riga "Tool" del detail panel (660 — `agent.current_tool.as_deref()`).
- Drop `subagent_info` (661-662 — "Subagents: N").
- Drop la funzione `format_tokens` se diventa unused.
- Drop ogni riga model nel detail panel (cerca "Model:" o `agent.model`).

In `state_file.rs`:
- Drop chiavi JSON `tokens_in`, `tokens_out` (94-95, 154-155).

In `agent.rs`:
- `AgentInfo` literal init (515-524): drop i campi rimossi.

In `main.rs`:
- Restore from save state (1424-1425): drop le righe `info.tokens_in = saved.tokens_in;` etc.
- StatusMessage literal (1354-1360): drop i campi rimossi.

**Why**

Semplifica drasticamente il modello dati. Riduce manutenzione degli hook nativi (token parsing in claude-status-hook era ~30 righe). Coerenza: nessun agente popolava questi campi in modo uniforme.

**No backward compat (decisione utente)**: file `.lince-dashboard` vecchi con `tokens_in` fields → o ignoriamo i campi extra via serde (preferibile per evitare panic), o lasciamo che il parsing fallisca e si rigeneri. Scegliere il path che evita crash.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AgentInfo non ha più i campi tokens_in/out, current_tool, model, running_subagents
- [ ] #2 Detail panel non mostra più righe Tokens/Tool/Subagents/Model
- [ ] #3 Tabella agenti non mostra più il suffix 'ₙ⚙' dei subagents
- [ ] #4 SavedAgentInfo non ha più i campi tokens, e il restore funziona (caricando file vecchi senza panic)
- [ ] #5 state_file.rs JSON non emette più tokens_in/tokens_out
- [ ] #6 apply_status_side_effects rimosso o ridotto a no-op
- [ ] #7 Compila senza warning su funzioni unused (es. format_tokens)
<!-- AC:END -->
