---
id: LINCE-124
title: Rename skill lince-setup → lince-add-supported-agent
status: In Progress
assignee: []
created_date: '2026-05-13 20:01'
updated_date: '2026-05-13 20:26'
labels: []
milestone: m-15
dependencies: []
references:
  - lince-dashboard/skills/lince-setup/SKILL.md
  - lince-dashboard/skills/install.sh
  - docs/documentation/dashboard/agent-examples.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Rinomina la skill `lince-setup` in `lince-add-supported-agent` per riflettere lo scopo reale (onboardare un nuovo agente nel dashboard).

**Changes**:

- `lince-dashboard/skills/lince-setup/` → `lince-dashboard/skills/lince-add-supported-agent/`
- Aggiorna SKILL.md frontmatter:
  - `name: lince-add-supported-agent`
  - `description:` aggiornata: "Add support for a new AI coding agent (or CLI tool) to lince-dashboard..."
  - `triggers`: aggiungi varianti tipo "add agent", "new agent type", "support cursor/bob/cli"
- Cerca tutti i riferimenti al vecchio nome `lince-setup` nel repo:
  - `lince-dashboard/skills/install.sh` (e analoghi update/uninstall)
  - `docs/documentation/dashboard/agent-examples.md` (linea 64+)
  - CLAUDE.md / README se citato
  - Eventuali altri SKILL.md o config che lo referenziano

- Aggiorna `lince-dashboard/skills/install.sh` per installare la skill nel nuovo path
- Lascia uno stub deprecation? **No**: l'utente ha detto no backward compat. Hard rename.

**Why**

Il nome attuale "lince-setup" è ambiguo (sembra setup generico del dashboard, non specifico per aggiungere agenti). Il nuovo nome:
- Auto-documenta lo scopo
- Si allinea col linguaggio in CONTRIBUTING.md (vedi LINCE-126)
- Riduce confusione con `lince-configure` (settings tweaking)

**Important**: questa task fa solo il rename mecccanico. Il restructure del contenuto della skill è in LINCE-125.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Directory rinominata: lince-dashboard/skills/lince-add-supported-agent/
- [x] #2 SKILL.md frontmatter name = `lince-add-supported-agent`
- [x] #3 install.sh installa la skill nel nuovo path utente (~/.claude/skills/lince-add-supported-agent/)
- [x] #4 update.sh / uninstall.sh aggiornati
- [x] #5 Vecchio path ~/.claude/skills/lince-setup/ viene rimosso dall'uninstall (cleanup) o dall'update (migration)
- [x] #6 Nessun riferimento testuale a `lince-setup` nel repo (eccetto eventuali changelog/note storiche)
- [ ] #7 Aggiornamento di `lince-dashboard/skills/install.sh` validato lanciandolo su un'installazione test
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation delegated to subagent. Plan = description in task body. Mechanical rename of skill directory + references.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Subagent (general claude) execution. agentId: a1d095a1958dfcbd5. AC7 (live install.sh validation) deferred to LINCE-123 — remaining `lince-setup` matches are intentional migration cleanup.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Directory renamed via git mv (history preserved): lince-dashboard/skills/lince-setup → lince-dashboard/skills/lince-add-supported-agent. SKILL.md frontmatter updated (name, description, added trigger keywords for "add agent", "new agent type", "support cursor/bob/cli", "register agent"). Body restructure left for LINCE-125. 8 files updated: SKILL.md, install.sh, update.sh, uninstall.sh, MULTI-AGENT-GUIDE.md, README.md, quickstart.sh, docs/documentation/dashboard/agent-examples.md. uninstall.sh and update.sh include migration-cleanup for legacy ~/.claude/skills/lince-setup/ path — these are the only intentional remaining references to the old name. Validation by actually running install.sh on a test install deferred to LINCE-123.
<!-- SECTION:FINAL_SUMMARY:END -->
