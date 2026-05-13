---
id: LINCE-122
title: Simplify hook scripts (Claude/Codex/Pi/OpenCode) + populate event_map TOML
status: To Do
assignee: []
created_date: '2026-05-13 20:01'
labels: []
milestone: m-15
dependencies:
  - LINCE-118
references:
  - lince-dashboard/hooks/claude-status-hook.sh
  - lince-dashboard/hooks/codex-status-hook.sh
  - lince-dashboard/hooks/pi/lince-pi-hook.ts
  - lince-dashboard/hooks/opencode-status-hook.js
  - lince-dashboard/agents-defaults.toml
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What**

Riduci tutti gli hook nativi al contratto minimale `{agent_id, event}` con event in `running|input|permission|stopped`. Sposta il mapping dai nomi nativi ai canonici nel TOML `event_map` per agente, così il codice Rust non ha più conoscenza di Claude/Codex/Pi specifici.

**Changes per hook script**:

`hooks/claude-status-hook.sh`:
- Drop estrazione e emissione di `tool_name`, `subagent_type`, `model`, `tokens_in`, `tokens_out` (linee 93, 131-138, 150-162)
- Drop eventi `subagent_start` / `subagent_stop` (96, 100) — la feature non esiste più
- Emetti solo JSON `{agent_id, event}` con event nei valori nativi Claude (`Stop`, `PreToolUse`, `idle_prompt`, `permission_prompt`). La mappatura ai canonici avviene nel dashboard via event_map.
- Lo script si riduce a ~30 righe (era ~170)

`hooks/codex-status-hook.sh`:
- Same trattamento: solo `{agent_id, event}`, niente token o tool

`hooks/pi/lince-pi-hook.ts`:
- Linea 30: `send("running", { tool_name: e.toolName })` → `send("running")`
- Tutti gli `send()` emettono solo l'evento, no extra fields

`hooks/opencode-status-hook.js`:
- Linea 88: drop `extra.tool_name = tool`

**Changes nel TOML defaults** (`lince-dashboard/agents-defaults.toml`):

Per ogni agente, popolare `event_map`:

```toml
[agents.claude]
has_native_hooks = true
[agents.claude.event_map]
Stop = "stopped"
PreToolUse = "running"
PostToolUse = "running"
idle_prompt = "input"
permission_prompt = "permission"

[agents.codex]
# verifica nomi eventi nativi di codex hook, mappare ai 4 canonici

[agents.pi]
# verifica eventi del Pi extension (session_start, turn_start, tool_call, turn_end, session_shutdown)
# mappare:
# session_start -> input (o running)
# tool_call -> running
# turn_end -> input
# session_shutdown -> stopped

[agents.opencode]
# se opencode-status-hook.js emette eventi specifici, mapparli; altrimenti drop has_native_hooks
```

**Verifica**: dopo questa task, gli hook scripts non hanno più logica condizionale "se evento X allora emetti Y" — emettono il nome nativo e il dashboard fa la traduzione.

**Why**

Centralizza il mapping nel TOML, dove la skill `lince-add-supported-agent` può generarlo automaticamente. Riduce drasticamente la complessità degli hook script (manutenzione = aggiornare eventi quando upstream cambia, che è il minimo necessario).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Ogni hook script emette solo JSON `{agent_id, event}` con event = nome nativo dell'agente
- [ ] #2 Nessun hook script emette più tool_name, tokens_in, tokens_out, model, subagent_type, subagent_start, subagent_stop
- [ ] #3 claude-status-hook.sh ridotto a <50 righe
- [ ] #4 agents-defaults.toml ha sezione `[agents.<key>.event_map]` per claude/codex/pi/opencode
- [ ] #5 Verifica manuale: Claude raggiunge tutti e 4 gli stati attivi (Running, INPUT, PERMISSION, Stopped) tramite event_map e non hardcoded logic
- [ ] #6 Codex transita correttamente tra i 4 stati attivi (verifica con il suo hook)
- [ ] #7 Pi (multi-provider) transita correttamente
<!-- AC:END -->
