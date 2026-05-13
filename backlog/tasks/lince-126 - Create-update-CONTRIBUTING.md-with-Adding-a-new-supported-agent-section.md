---
id: LINCE-126
title: Create/update CONTRIBUTING.md with "Adding a new supported agent" section
status: Done
assignee: []
created_date: '2026-05-13 20:02'
updated_date: '2026-05-13 20:46'
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
- [x] #1 CONTRIBUTING.md esiste alla root del repo
- [x] #2 Sezione 'Adding a new supported agent' presente con Tier model spiegato
- [x] #3 Cita la skill `lince-add-supported-agent` come entry point
- [x] #4 Documenta brevemente l'hook contract e linka allo SKILL.md per dettagli
- [x] #5 Spiega policy 'in-tree vs user-side' (Tier C → issue prima del PR)
- [x] #6 Coerente con SKILL.md, no duplicazione di contenuti tecnici
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Wave 3 parallel. Delegated to subagent. Create CONTRIBUTING.md (or update if exists) with Adding-a-new-supported-agent section. 3-tier model, references to the skill, hook contract summary.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Subagent (technical-writer) execution. agentId: a70a0a1040759ea7c. No markdownlint installed; manual inspection confirms valid markdown.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CONTRIBUTING.md updated (was pre-existing, 157 lines). Added "Adding a new supported agent" section (78 lines) between "Development setup" and "Code style" — logical placement after install-scripts discipline, before general code-style rules. New section content: tier model table (A/B/C with examples + maintenance), quick start with /lince-add-supported-agent invocation, hook contract summary (minimal JSON, 5 canonical states), "what goes in repo vs user-side" policy, "when to promote Tier C → Tier A/B" governance with "issue before PR" rule. Links resolved: SKILL.md, agents-defaults.toml (dashboard + sandbox modules). No duplication of technical content — points to SKILL.md for hook templates and full decision tree. File total: 234 lines.
<!-- SECTION:FINAL_SUMMARY:END -->
