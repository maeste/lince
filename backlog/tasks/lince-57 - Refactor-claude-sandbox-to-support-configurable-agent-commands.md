---
id: LINCE-57
title: Refactor claude-sandbox to support configurable agent commands
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
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

**Why**: The sandbox must wrap any CLI agent (Codex, Gemini, OpenCode), not just Claude Code. This is the sandbox-side foundation for multi-agent support.

**Implementation scope**:
- `build_bwrap_cmd()` accepts `agent_command` parameter instead of hardcoding `"claude"`
- New config sections: `[agents.claude]`, `[agents.codex]`, `[agents.gemini]`, `[agents.opencode]` with fields: `command`, `default_args`, `env`
- New `--agent` CLI flag on `run` subcommand (default: "claude")
- Backward compat: existing `[claude]` section mapped to `[agents.claude]`

**Key file**: `sandbox/claude-sandbox`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 build_bwrap_cmd() accepts agent_command parameter, no hardcoded 'claude'
- [ ] #2 Config supports [agents.<name>] sections with command, default_args, env fields
- [ ] #3 --agent CLI flag works on run subcommand (default: 'claude')
- [ ] #4 claude-sandbox run --agent codex -p /project produces correct bwrap command
- [ ] #5 Existing [claude] config section still works (backward compat)
- [ ] #6 claude-sandbox run -p /project (no --agent) behaves identically to current behavior
<!-- AC:END -->
