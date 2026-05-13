---
id: LINCE-124
title: Rename skill lince-setup → lince-add-supported-agent
status: To Do
assignee: []
created_date: '2026-05-13 20:01'
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
- [ ] #1 Directory rinominata: lince-dashboard/skills/lince-add-supported-agent/
- [ ] #2 SKILL.md frontmatter name = `lince-add-supported-agent`
- [ ] #3 install.sh installa la skill nel nuovo path utente (~/.claude/skills/lince-add-supported-agent/)
- [ ] #4 update.sh / uninstall.sh aggiornati
- [ ] #5 Vecchio path ~/.claude/skills/lince-setup/ viene rimosso dall'uninstall (cleanup) o dall'update (migration)
- [ ] #6 Nessun riferimento testuale a `lince-setup` nel repo (eccetto eventuali changelog/note storiche)
- [ ] #7 Aggiornamento di `lince-dashboard/skills/install.sh` validato lanciandolo su un'installazione test
<!-- AC:END -->
