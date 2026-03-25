---
id: LINCE-57
title: Refactor claude-sandbox to support configurable agent commands
status: Done
assignee: []
created_date: '2026-03-20 17:42'
updated_date: '2026-03-24 20:45'
labels:
  - sandbox
  - refactor
  - multi-agent
  - foundation
milestone: m-12
dependencies: []
references:
  - sandbox/claude-sandbox
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently `build_bwrap_cmd()` hardcodes `claude` as the inner command (line ~418). Refactor to accept the inner command from config, making the sandbox agent-agnostic.

**Why**: The sandbox must wrap any CLI agent, not just Claude Code. This is the sandbox-side foundation for multi-agent support.

**Implementation scope**:
- `build_bwrap_cmd()` accepts `agent_command` parameter instead of hardcoding `"claude"`
- New config sections: `[agents.<name>]` with fields: `command`, `default_args`, `env`, `home_ro_dirs`, `home_rw_dirs`, `bwrap_conflict`, `disable_inner_sandbox_args` — matching the dashboard's `AgentTypeConfig` fields
- Defaults loaded from external `agents-defaults.toml` (same file the dashboard uses), merged with user config
- New `--agent` CLI flag on `run` subcommand (default: "claude")
- Agent name is a free-form string key, not an enum — any key present in config is valid
- Backward compat: existing `[claude]` section mapped to `[agents.claude]`

**Key file**: `sandbox/claude-sandbox`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 build_bwrap_cmd() accepts agent_command parameter, no hardcoded 'claude'
- [x] #2 Config supports [agents.<name>] sections with command, default_args, env, home_ro_dirs, home_rw_dirs, bwrap_conflict, disable_inner_sandbox_args
- [x] #3 --agent CLI flag works on run subcommand (default: 'claude')
- [x] #4 Agent name is a free-form string key — any name in config is valid
- [x] #5 Defaults loaded from agents-defaults.toml, merged with user config (user wins)
- [x] #6 claude-sandbox run --agent codex -p /project produces correct bwrap command
- [x] #7 Existing [claude] config section still works (backward compat)
- [x] #8 claude-sandbox run -p /project (no --agent) behaves identically to current behavior
<!-- AC:END -->
