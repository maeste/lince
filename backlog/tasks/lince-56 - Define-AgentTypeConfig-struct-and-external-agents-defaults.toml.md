---
id: LINCE-56
title: Define AgentTypeConfig struct and external agents-defaults.toml
status: Done
assignee: []
created_date: '2026-03-20 17:42'
updated_date: '2026-03-24 20:45'
labels:
  - dashboard
  - config
  - foundation
  - multi-agent
milestone: m-12
dependencies: []
references:
  - lince-dashboard/plugin/src/config.rs
  - agents-defaults.toml
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The dashboard currently has no concept of agent type — everything is hardcoded to Claude Code. Add a generic `AgentTypeConfig` struct and ship built-in presets via an external `agents-defaults.toml` file.

**Why**: This is the foundational abstraction that all other multi-agent tasks depend on. Agents are identified by string keys (not an enum) — any agent is just a shell command + env vars + bind mounts + display metadata + status config.

**Design decision**: No `AgentType` enum. The enum adds complexity without buying anything that config fields don't provide. The `Custom` variant in the original design already admitted agents can't be fully enumerated. With pure config, adding a new agent requires zero code changes — just a TOML section.

**Implementation scope**:
- `AgentTypeConfig` struct in `config.rs` with fields: `command` (Vec template with placeholders `{agent_id}`, `{project_dir}`, `{profile}`), `pane_title_pattern`, `status_pipe_name`, `display_name`, `short_label` (3 char for table), `color` (ANSI), `sandboxed` (bool), `env_vars` (HashMap), `has_native_hooks` (bool), `home_ro_dirs`, `home_rw_dirs`, `bwrap_conflict` (bool), `disable_inner_sandbox_args` (Vec), `event_map` (optional HashMap)
- `DashboardConfig` gains `agent_types: HashMap<String, AgentTypeConfig>` populated from external `agents-defaults.toml` merged with user `[agents.*]` TOML sections
- External `agents-defaults.toml` shipped alongside plugin with presets for: claude, claude-unsandboxed, codex, gemini, opencode
- Config loading order: `agents-defaults.toml` → user `config.toml` `[agents.*]` sections (user overrides defaults)
- Install scripts deploy defaults file to `~/.claude-sandbox/agents-defaults.toml`

**Key files**: `plugin/src/config.rs`, `agents-defaults.toml` (new), install scripts
**Constraint**: All file I/O must use `run_command()`, not `std::fs` (WASI sandbox limitation)

**Absorbed tasks**: This replaces separate integration tasks for each agent (formerly LINCE-68, 69, 70, 71) — those are now just preset entries in agents-defaults.toml.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AgentTypeConfig struct has all specified fields: command, pane_title_pattern, status_pipe_name, display_name, short_label, color, sandboxed, env_vars, has_native_hooks, home_ro_dirs, home_rw_dirs, bwrap_conflict, disable_inner_sandbox_args, event_map
- [x] #2 No AgentType enum exists — agents identified by string keys only
- [x] #3 DashboardConfig.agent_types is HashMap<String, AgentTypeConfig> populated from TOML
- [x] #4 External agents-defaults.toml ships with presets for claude, claude-unsandboxed, codex, gemini, opencode
- [x] #5 Config loading merges defaults with user overrides (user wins)
- [x] #6 User can define a completely new agent via TOML with zero code changes
- [x] #7 Plugin compiles successfully for wasm32-wasip1 target
- [ ] #8 Install scripts deploy agents-defaults.toml to correct location
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AC #8 (install scripts deploy agents-defaults.toml) deferred to LINCE-72 which covers install script updates. Warning: AgentDefaultsFile struct unused — minor, can clean up later.
<!-- SECTION:NOTES:END -->
