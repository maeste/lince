---
id: LINCE-125
title: >-
  Restructure skill SKILL.md as agent onboarding guide (3-tier model + hook
  templates)
status: Done
assignee: []
created_date: '2026-05-13 20:01'
updated_date: '2026-05-13 20:38'
labels: []
milestone: m-15
dependencies:
  - LINCE-124
references:
  - lince-dashboard/skills/lince-add-supported-agent/SKILL.md
  - lince-dashboard/skills/lince-add-supported-agent/scripts/validate-agent.sh
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Ristruttura `SKILL.md` della skill rinominata in modo che sia la guida ufficiale di onboarding per un nuovo agente, con il 3-tier model.

**Sezioni nel nuovo SKILL.md**:

**1. Overview & Tier Model**

Spiega i 3 tier:
- **Tier A — Native hooks**: l'agente espone un meccanismo hook (es. Claude PreToolUse/Stop, Codex notify hook). Output: TOML completo + hook script template + entry `event_map` nei defaults TOML.
- **Tier B — Wrapper-only (Unknown state)**: l'agente non ha hook nativi (es. bash, gh, Bob). Mostra `-` sempre. Output: solo TOML.
- **Tier C — User contribution**: agenti aggiunti dall'utente tramite questa skill, salvati in `~/.agent-sandbox/config.toml` + `~/.config/lince-dashboard/config.toml`. Non finiscono nel repo, l'utente li mantiene.

**2. Decision tree (domande iniziali)**

1. Binary name + install path?
2. Config directory (`~/.xxx/`)?
3. API keys env vars (se any)?
4. Internal sandbox conflict? (bwrap/Docker — se sì, args per disabilitarlo)
5. **Has native hooks?** Y/N → seleziona Tier A o B
6. Se A: in che linguaggio l'hook? (bash, TS, JS) — genera template appropriato

**3. Generation steps**

- Genera sezione TOML sandbox (`~/.agent-sandbox/config.toml` `[agents.<key>]`)
- Genera sezione TOML dashboard (`~/.config/lince-dashboard/config.toml` `[agents.<key>]`)
- Se Tier A:
  - Genera template hook script (~/.local/share/lince/hooks/<key>-status-hook.sh o equivalente)
  - Template emette JSON `{agent_id, event}` su pipe — l'utente personalizza i mapping
  - Genera entry `[agents.<key>.event_map]` con valori placeholder
  - Spiega come testare l'hook (esempio: `echo '{"agent_id":"test","event":"running"}' | zellij pipe --name lince-status`)
- Se Tier B: salta la parte hook, dice esplicitamente "questo agente mostrerà 'Unknown' nel dashboard, che è il comportamento corretto"

**4. Examples (riferimenti)**

- Tier A esemplare: Claude (link al hook script, all'event_map)
- Tier A esemplare semplice: Codex (5 eventi, hook ~30 righe)
- Tier B esemplare: bash, Gemini
- Tier C riferimento: dove l'utente trova i suoi agenti custom

**5. Validation script**

Aggiorna `scripts/validate-agent.sh` (o equivalente) per:
- Validare la sezione TOML generata
- Se Tier A: validare che lo script emetta JSON parsabile dal contratto pubblico
- Esegue un dry-run: `agent-sandbox run --agent <key> --dry-run` se supportato

**6. Hook contract specification**

Documenta il contratto pipe come prima sezione tecnica:
- Pipe name: configurabile via `status_pipe_name`, default `lince-status`
- JSON shape: `{"agent_id": string, "event": "running"|"input"|"permission"|"stopped"}`
- Event semantics:
  - `running`: agente sta lavorando attivamente
  - `input`: agente in attesa di input utente (turno utente)
  - `permission`: agente richiede approvazione esplicita (es. tool use)
  - `stopped`: agente terminato (volontariamente o per errore)
- Eventi sconosciuti vengono mappati a `Unknown` (silent fallback rimosso)

**Why**

La skill diventa il single source of truth per onboardare un agente. Eliminare la documentazione duplicata in altri posti. Massimizzare la chance che un contributor (interno o esterno) generi configurazione corretta al primo colpo.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SKILL.md ha sezione Tier Model con i 3 tier descritti
- [x] #2 SKILL.md documenta il contratto pipe + 4 eventi canonici con semantica
- [x] #3 Decision tree presente: porta a Tier A o B basato sulle risposte
- [x] #4 Template hook script generato per Tier A in shell (almeno) e TS (opzionale)
- [x] #5 Esempi linkano a hook esistenti come reference (Claude, Codex)
- [x] #6 Validation script aggiornato per supportare il check del nuovo contratto
- [ ] #7 Skill testata manualmente generando configurazione per un agente fittizio (Tier A + Tier B)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Wave 2A parallel. Delegated to subagent. Restructure SKILL.md body for the renamed skill (lince-add-supported-agent) as comprehensive 3-tier onboarding guide; add hook contract spec + template generators. Frontmatter already updated in LINCE-124.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Subagent (technical-writer) execution. agentId: aa0916c4c751f2491. validate-agent.sh syntax verified.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
SKILL.md body rewritten as comprehensive agent onboarding guide (294 LOC, under 400 cap). New body structure: (1) Overview & Tier Model with explicit "if uncertain pick B, promote later" guidance; (2) Hook Contract — minimal {agent_id, event} JSON, 5-state canonical table, dashboard resolution order, pipe test command; (3) Decision tree — 6 ordered questions ending in tier choice + hook-language pick; (4) Generation steps — sandbox/dashboard TOML sections, Tier A event_map + inline bash hook template, Tier B explicit "show '-' is expected"; (5) Examples — Claude (rich), Codex (lean), Gemini/shells (Tier B), kiro (Tier C) with real in-repo paths; (6) Validate via scripts/validate-agent.sh. Files modified: SKILL.md, references/config-schema.md, references/examples.md, scripts/validate-agent.sh. Files added: references/hook-templates.md (bash + TS/JS skeletons). validate-agent.sh rewritten to use python3 tomllib parsing (vs prior grep heuristics) with tier-aware validation: Tier A requires hook script + canonical-only event_map values; Tier B forbids both. PASS/FAIL summary with non-zero exit on FAIL. Smoke-tested across 3 scenarios. AC7 (manual full skill run) deferred to LINCE-123.
<!-- SECTION:FINAL_SUMMARY:END -->
