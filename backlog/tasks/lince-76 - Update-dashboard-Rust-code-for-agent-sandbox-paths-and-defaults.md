---
id: LINCE-76
title: Update dashboard Rust code for agent-sandbox paths and defaults
status: Done
assignee: []
created_date: '2026-03-25 09:19'
updated_date: '2026-03-25 09:27'
labels:
  - dashboard
  - rename
milestone: m-12
dependencies:
  - LINCE-74
references:
  - lince-dashboard/plugin/src/config.rs
  - lince-dashboard/plugin/src/agent.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update all hardcoded `claude-sandbox` references in the dashboard plugin Rust code — config paths, default sandbox command, pane title patterns, doc comments.

**Why**: The dashboard must reference the renamed sandbox binary and config directory.

**Implementation plan**:
1. **config.rs**:
   - `default_sandbox_command()` → return `\"agent-sandbox\"` instead of `\"claude-sandbox\"`
   - Default config path: `~/.claude-sandbox/config.toml` → `~/.agent-sandbox/config.toml`
   - Agent defaults path: `~/.claude-sandbox/agents-defaults.toml` → `~/.agent-sandbox/agents-defaults.toml`
   - Local config path pattern: `{}/.claude-sandbox/config.toml` → `{}/.agent-sandbox/config.toml`
   - Update all doc comments
2. **agent.rs**:
   - Pane title fallback pattern: `\"claude-sandbox\"` → `\"agent-sandbox\"`
   - Legacy fallback in `spawn_inner()` uses `config.sandbox_command` (auto-updated via config default)
3. Build: `PATH=\"$HOME/.cargo/bin:$PATH\" cargo build --target wasm32-wasip1`
4. Verify zero warnings

**~15 reference changes across 2 files.**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Default sandbox command is 'agent-sandbox' in config.rs default_sandbox_command()
- [x] #2 Config path defaults use ~/.agent-sandbox/config.toml
- [x] #3 Agent defaults path uses ~/.agent-sandbox/agents-defaults.toml
- [x] #4 Pane title fallback pattern is 'agent-sandbox'
- [x] #5 Plugin compiles for wasm32-wasip1 with zero warnings
- [x] #6 Existing behavior unchanged — config values override defaults
<!-- AC:END -->
