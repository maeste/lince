---
id: LINCE-127
title: >-
  Update docs/documentation/dashboard/agent-examples.md for 5-state + new skill
  name
status: To Do
assignee: []
created_date: '2026-05-13 20:02'
labels: []
milestone: m-15
dependencies:
  - LINCE-124
  - LINCE-125
references:
  - docs/documentation/dashboard/agent-examples.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Aggiorna `docs/documentation/dashboard/agent-examples.md` per riflettere:
- Nome skill `lince-add-supported-agent` (era `lince-setup`)
- 5-state model con label/colori canonici
- Hook contract semplificato a 4 eventi
- 3-tier model

**Cosa cambia nel doc**:

- Sezione "Adding a Custom Agent" (linea 64+):
  - Cambia nome skill in ogni occorrenza
  - Aggiorna gli esempi TOML per riflettere il nuovo schema (event_map presente, has_native_hooks chiaro)
  - Aggiungi nota sul Tier model: "your agent will fall into one of these tiers..."
  - Drop ogni riferimento a `tokens_in/out`, `tool_name`, `model`, `subagent_*` fields (non esistono più)

- Sezione status (se esiste): aggiorna la lista degli stati visibili nel dashboard ai 5 canonici con i loro label/colori.

- Esempi di hook script: aggiorna ogni snippet per emettere il JSON minimale `{agent_id, event}`.

**Verifica anche**:
- `docs/documentation/dashboard/` altri file: cerca riferimenti a "tokens" o "current_tool" — rimuovi
- Website (se presente in `lince-dashboard/website/`): cerca testi obsoleti — aggiorna

**Why**

La documentazione è il primo posto dove un utente nuovo cerca informazioni. Inconsistenze tra doc, skill, e codice generano confusione e ticket di supporto.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agent-examples.md cita `lince-add-supported-agent` invece di `lince-setup`
- [ ] #2 Esempi TOML aggiornati: presente `event_map`, niente campi rimossi
- [ ] #3 Sezione status documenta i 5 stati canonici (Unknown/Running/INPUT/PERMISSION/Stopped) con label e colori
- [ ] #4 Nessun riferimento a tokens_in, tokens_out, current_tool, tool_name, model, running_subagents, subagent_start, subagent_stop
- [ ] #5 Esempi di hook emettono JSON minimale {agent_id, event}
- [ ] #6 Scan ricorsivo di docs/ e website/ per riferimenti obsoleti effettuato
<!-- AC:END -->
