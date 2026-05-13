---
id: LINCE-126
title: Create/update CONTRIBUTING.md with "Adding a new supported agent" section
status: To Do
assignee: []
created_date: '2026-05-13 20:02'
labels: []
milestone: m-15
dependencies:
  - LINCE-125
references:
  - lince-dashboard/skills/lince-add-supported-agent/SKILL.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Crea `CONTRIBUTING.md` (se non esiste) o aggiungi una sezione "Adding a new supported agent" che cita la skill come entry point canonical.

**Verifica iniziale**: controlla se CONTRIBUTING.md esiste nel repo. Se sì, aggiungi sezione. Se no, crea il file con scaffolding base + la sezione mirata.

**Contenuto sezione**:

```markdown
## Adding a new supported agent

LINCE supports any CLI-based AI coding agent. To add support for a new one,
use the `lince-add-supported-agent` skill (installed automatically with the
dashboard).

### Quick start

In a Claude Code session inside this repo:

```
/lince-add-supported-agent
```

The skill walks you through a decision tree, generates the right TOML
configuration, and (if applicable) a hook script template you can customize.

### Tier model

LINCE recognizes three tiers of agent support:

- **Tier A — Native hooks** (e.g. Claude, Codex, Pi): the agent exposes
  lifecycle hooks. Full status reporting: Running / INPUT / PERMISSION /
  Stopped. Native hook scripts live in `lince-dashboard/hooks/` and are
  mapped to canonical events via `event_map` in `agents-defaults.toml`.
- **Tier B — Wrapper-only** (e.g. bash, gh, Gemini): no native hooks. Shows
  `-` (Unknown) for the lifetime of the agent. Honest about not knowing
  what's happening inside. Only TOML configuration needed.
- **Tier C — User-contributed**: agents added via the skill, persisted in
  user-side config (`~/.agent-sandbox/config.toml` and
  `~/.config/lince-dashboard/config.toml`). Not in the repo. The user
  maintains them.

### Hook contract

Native hooks emit JSON to a Zellij pipe (default name: `lince-status`):

```json
{"agent_id": "<id>", "event": "running"|"input"|"permission"|"stopped"}
```

Unknown events are mapped to the `Unknown` status (no silent fallback).

For event semantics, hook templates, and the full contract reference, see
the `lince-add-supported-agent` skill documentation.

### What goes in the repo vs. user-side

- Tier A and Tier B agents that ship with LINCE → `lince-dashboard/agents-defaults.toml`,
  `sandbox/agents-defaults.toml`, and any hook scripts in `lince-dashboard/hooks/`.
- Custom agents added by users → user config files only. Not PR-able as
  Tier A/B unless we explicitly want to support them in-tree (high bar:
  ongoing maintenance burden of tracking upstream changes).

### When to promote a Tier C agent to Tier A/B (in-tree)

We add an agent in-tree when:
- It's a widely-used CLI agent that benefits multiple users
- We're willing to take on ongoing maintenance (upstream change tracking)
- It has stable hook semantics (Tier A) or its absence of state is acceptable (Tier B)

Open an issue with the proposal before sending a PR.
```

**Why**

- Dà ai contributor un punto di ingresso chiaro
- Esplicita la nostra policy di Tier model (e quindi limiti di crescita di Tier A)
- Riduce richieste future di tipo "support agent X nativamente" senza un canale strutturato

**Verifica**: il documento deve essere coerente con il SKILL.md della skill (LINCE-125) — niente duplicazione, il CONTRIBUTING punta alla skill per i dettagli.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CONTRIBUTING.md esiste alla root del repo
- [ ] #2 Sezione 'Adding a new supported agent' presente con Tier model spiegato
- [ ] #3 Cita la skill `lince-add-supported-agent` come entry point
- [ ] #4 Documenta brevemente l'hook contract e linka allo SKILL.md per dettagli
- [ ] #5 Spiega policy 'in-tree vs user-side' (Tier C → issue prima del PR)
- [ ] #6 Coerente con SKILL.md, no duplicazione di contenuti tecnici
<!-- AC:END -->
