---
id: LINCE-127
title: >-
  Update docs/documentation/dashboard/agent-examples.md for 5-state + new skill
  name
status: Done
assignee: []
created_date: '2026-05-13 20:02'
updated_date: '2026-05-13 20:51'
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
- [x] #1 agent-examples.md cita `lince-add-supported-agent` invece di `lince-setup`
- [x] #2 Esempi TOML aggiornati: presente `event_map`, niente campi rimossi
- [x] #3 Sezione status documenta i 5 stati canonici (Unknown/Running/INPUT/PERMISSION/Stopped) con label e colori
- [x] #4 Nessun riferimento a tokens_in, tokens_out, current_tool, tool_name, model, running_subagents, subagent_start, subagent_stop
- [x] #5 Esempi di hook emettono JSON minimale {agent_id, event}
- [x] #6 Scan ricorsivo di docs/ e website/ per riferimenti obsoleti effettuato
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Wave 4 final. Delegated to subagent. Update agent-examples.md and any other docs referencing the old 7-state model, rich fields, or old skill name. The 5-state model + minimal hook contract + 3-tier model must be reflected.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Subagent (technical-writer) execution. agentId: a923558cafe3d9973. 6 files updated. Two sweeps post-edit confirm no stragglers.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Final m-15 doc sync complete across 6 files. agent-examples.md: Default Agent Types table corrected (native_hooks column matches agents-defaults.toml), tier-model summary added, manual configuration step list now includes has_native_hooks + event_map, full Tier A example (claude) and Tier B example (bash) added, Status Reporting section replaced (5-state canonical table + minimal {agent_id, event} contract; rich-payload field table dropped; subagent_start/stop and wrapper-start events documented as removed). usage-guide.md: Agent Lifecycle rewritten (- initial, not Starting), Status Colors table replaced with 5-state, Detail Panel cleaned of Token/Tool/Subagent/Error rows, Session Save&Restore note about ignored legacy fields added (intentional history reference). config-reference.md: ignore_wrapper_start row removed, event_map row updated to require canonical values. README.md root: dashboard mock-up cleaned (no Tokens column, Idle→-), "Real-time status" feature bullet references 5 canonical states. skill references/config-schema.md + examples.md: ignore_wrapper_start removed from field table + Codex example. Cross-doc sweep clean: only the deliberate history note in usage-guide.md matches the obsolete-field grep; old skill name `lince-setup` returns zero hits in markdown files. Files NOT touched: lince-dashboard/MULTI-AGENT-GUIDE.md (LINCE-124 already clean), all README.md and CONTRIBUTING.md (already current). No website/ directory exists.
<!-- SECTION:FINAL_SUMMARY:END -->
