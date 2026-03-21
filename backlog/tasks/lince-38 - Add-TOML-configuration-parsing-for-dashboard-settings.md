---
id: LINCE-38
title: Add TOML configuration parsing for dashboard settings
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:38'
updated_date: '2026-03-19 13:06'
labels:
  - dashboard
  - config
  - rust
milestone: m-10
dependencies:
  - LINCE-37
references:
  - sandbox/config.toml.example
  - voxcode/config.toml
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add TOML config parsing to the dashboard plugin. Config controls default agent profile, sandbox command path, layout mode, focus mode, status method, and limits.

## Implementation Plan

1. Add `toml` and `serde` crates to `Cargo.toml` (both pure Rust, WASM-compatible)
2. Create `src/config.rs`:
   - Define enums: `AgentLayout { Single, Multi }`, `FocusMode { Replace, Floating }`, `StatusMethod { Pipe, File }`
   - Define `DashboardConfig` struct:
     - `default_profile: Option<String>`
     - `default_project_dir: Option<String>`
     - `sandbox_command: String = "claude-sandbox"`
     - `agent_layout: AgentLayout = Single`
     - `focus_mode: FocusMode = Floating`
     - `status_method: StatusMethod = Pipe`
     - `status_file_dir: String = "/tmp"`
     - `max_agents: usize = 8`
   - Implement `Default` for `DashboardConfig`
   - Implement `DashboardConfig::load(path: &str) -> Self` — reads file, parses TOML, falls back to defaults on error
3. Create `lince-dashboard/config.toml` with documented defaults
4. In `main.rs`: add `mod config;`, load config in `State::load()` using path from plugin configuration (`plugin location="..." { config_path "/path/to/config.toml" }`)
5. Config path read via `zellij_tile::prelude::get_plugin_ids()` or plugin configuration map
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 src/config.rs exists with DashboardConfig struct, enums, and parsing logic
- [x] #2 lince-dashboard/config.toml exists with all options documented as comments
- [x] #3 Missing config file falls back to defaults without crashing
- [x] #4 Invalid TOML shows a warning in render but does not panic
- [x] #5 Plugin still compiles to WASM and loads
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Added `serde` (with derive) and `toml = \"0.8\"` to Cargo.toml\n2. Created `src/config.rs` with AgentLayout/FocusMode/StatusMethod enums, DashboardConfig struct with serde defaults, DashboardConfigFile wrapper for [dashboard] TOML table, and `load()` returning (config, Option<error>)\n3. Created `lince-dashboard/config.toml` with all options documented\n4. Updated `src/lib.rs` to load config from Zellij plugin configuration map's `config_path` key\n5. Config errors shown as status message in dashboard render
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-38 Completed\n\n### Files created\n- `src/config.rs` — DashboardConfig with serde deserialization, TOML loading, default fallback\n- `config.toml` — documented default configuration\n\n### Files modified\n- `Cargo.toml` — added serde + toml deps\n- `src/lib.rs` — integrated config loading in load(), config error display in render()\n\n### Key decisions\n- Used DashboardConfigFile wrapper for `[dashboard]` table prefix\n- load() returns (config, Option<error>) tuple — never panics\n- Config path passed via Zellij plugin configuration map (config_path key in KDL)
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All config fields have sensible defaults documented in code and config.toml
- [x] #2 Plugin loads with and without config file present
- [x] #3 Unit-level parse test documented (valid TOML string to correct struct values)
<!-- DOD:END -->
