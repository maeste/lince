---
id: LINCE-56
title: Define AgentType enum and per-type configuration struct
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
labels:
  - dashboard
  - types
  - config
  - foundation
milestone: m-12
dependencies: []
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/config.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The dashboard currently has no concept of agent type — everything is hardcoded to Claude Code. Add an `AgentType` enum and `AgentTypeConfig` struct to support multiple agent types via configuration.

**Why**: This is the foundational abstraction that all other multi-agent tasks depend on. Without a type system for agents, we cannot parameterize spawning, status detection, or rendering.

**Implementation scope**:
- `AgentType` enum in `types.rs`: Claude, ClaudeUnsandboxed, Codex, Gemini, OpenCode, Custom
- `AgentTypeConfig` struct in `config.rs` with fields: `command` (Vec template with placeholders `{agent_id}`, `{project_dir}`, `{profile}`), `pane_title_pattern`, `status_pipe_name`, `display_name`, `short_label` (3 char for table), `color` (ANSI), `sandboxed` (bool), `env_vars` (HashMap)
- Built-in defaults compiled for all known agent types
- `DashboardConfig` gains `agent_types: HashMap<String, AgentTypeConfig>` populated from `[agent_types.<name>]` TOML sections merged with defaults

**Key files**: `plugin/src/types.rs`, `plugin/src/config.rs`
**Constraint**: All file I/O must use `run_command()`, not `std::fs` (WASI sandbox limitation)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AgentType enum exists with variants: Claude, ClaudeUnsandboxed, Codex, Gemini, OpenCode, Custom
- [ ] #2 AgentTypeConfig struct has all specified fields: command, pane_title_pattern, status_pipe_name, display_name, short_label, color, sandboxed, env_vars
- [ ] #3 Built-in defaults are compiled for Claude, ClaudeUnsandboxed, Codex, Gemini, OpenCode
- [ ] #4 DashboardConfig.agent_types is populated from TOML with defaults merged in
- [ ] #5 Plugin compiles successfully for wasm32-wasip1 target
<!-- AC:END -->
