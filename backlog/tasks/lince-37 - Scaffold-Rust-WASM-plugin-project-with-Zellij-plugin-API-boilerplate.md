---
id: LINCE-37
title: Scaffold Rust WASM plugin project with Zellij plugin API boilerplate
status: To Do
assignee: []
created_date: '2026-03-19 10:37'
labels:
  - dashboard
  - skeleton
  - rust
milestone: m-10
dependencies: []
references:
  - zellij-setup/configs/config.kdl (load_plugins section)
  - zellij-setup/configs/three-pane.kdl
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `lince-dashboard/plugin/` with a minimal Zellij WASM plugin that compiles and loads in Zellij 0.43.x. The plugin is a Rust crate targeting `wasm32-wasip1` using the `zellij-tile` SDK.

## Implementation Plan

1. Create directory structure: `lince-dashboard/plugin/src/`
2. Create `Cargo.toml`:
   - `crate-type = ["cdylib"]`
   - Depend on `zellij-tile` 0.43.x
   - `[profile.release]` with `opt-level = "s"`, `lto = true`
3. Create `src/main.rs`:
   - Define `State` struct with `agents: Vec<()>`, `rows: usize`, `cols: usize`
   - Implement `ZellijPlugin` trait: `load()`, `update()`, `render()`
   - In `load()`: subscribe to `Key`, `Timer`, `PaneUpdate`, `ModeUpdate`, `RunCommandResult`, `CustomMessage`, `PermissionRequestResult`
   - Request permissions: `RunCommands`, `ChangeApplicationState`, `ReadApplicationState`, `MessageAndLaunchOtherPlugins`, `OpenTerminalsOrPlugins`
   - In `render()`: print "LINCE Dashboard" header
   - Use `register_plugin!(State)` macro
4. Create `build.sh`:
   - Check `wasm32-wasip1` target installed (`rustup target add wasm32-wasip1` if missing)
   - Run `cargo build --release --target wasm32-wasip1`
   - Copy `.wasm` from `target/wasm32-wasip1/release/` to `lince-dashboard/plugin/lince-dashboard.wasm`
5. Test: add `plugin location="file:/path/to/lince-dashboard.wasm"` to a layout, start Zellij
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 lince-dashboard/plugin/Cargo.toml exists with correct crate-type, zellij-tile dependency, WASM profile
- [ ] #2 src/main.rs implements ZellijPlugin trait with load/update/render
- [ ] #3 build.sh produces a .wasm file under 1 MB
- [ ] #4 Plugin loads in Zellij 0.43.x and displays 'LINCE Dashboard' text in its pane
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Code compiles with zero warnings on wasm32-wasip1
- [ ] #2 build.sh is executable and succeeds on a clean checkout
- [ ] #3 Manual test: plugin loads in Zellij without permission errors
<!-- DOD:END -->
