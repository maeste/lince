---
id: m-15
title: "m-15: Agent status simplification (5-state model)"
---

## Description

Semplifica drasticamente il modello di status del dashboard a 5 stati canonici (`-`/Running/INPUT/PERMISSION/Stopped) per ridurre la manutenzione degli hook nativi e abbassare la barriera per onboardare nuovi agenti CLI.

**Obiettivi**:
1. 5 stati canonici, nessuna variante extra (drop Starting/Idle/Error)
2. Drop totale dei campi rich dal contratto pubblico e dalla UI: `tokens_in/out`, `current_tool`/`tool_name`, `model`, `running_subagents`/`subagent_*` events
3. Contratto pipe ridotto a `{agent_id, event: "running"|"input"|"permission"|"stopped"}`
4. Agenti senza hook nativi mostrano `-` (Unknown) anziché "Running" eterno
5. Skill `lince-setup` rinominata `lince-add-supported-agent` e ristrutturata come guida ufficiale di onboarding (3-tier: A nativo, B Unknown, C contribuzione esterna)
6. CONTRIBUTING.md cita la skill come entry point canonical
7. No backward compatibility: vecchi file di stato si rigenerano

**Issue chiuse**: #116 (status transitions Running/Input + Unknown state)
**Issue parking**: #121 (Cursor), #122 (gh), #123 (Bob) — bloccate fino a m-15 conclusa, poi diventano "first dogfood" della nuova skill
