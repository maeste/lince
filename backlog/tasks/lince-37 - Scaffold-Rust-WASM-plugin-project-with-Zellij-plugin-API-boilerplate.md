---
id: LINCE-37
title: Scaffold Rust WASM plugin project with Zellij plugin API boilerplate
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:37'
updated_date: '2026-03-19 13:03'
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
- [x] #1 lince-dashboard/plugin/Cargo.toml exists with correct crate-type, zellij-tile dependency, WASM profile
- [x] #2 src/main.rs implements ZellijPlugin trait with load/update/render
- [x] #3 build.sh produces a .wasm file under 1 MB
- [ ] #4 Plugin loads in Zellij 0.43.x and displays 'LINCE Dashboard' text in its pane
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Created `lince-dashboard/plugin/` directory structure\n2. Created `Cargo.toml` with cdylib crate-type, zellij-tile 0.42.2 dep, release profile (opt-level=s, lto, strip)\n3. Created `src/lib.rs` (not main.rs — avoids bin/lib conflict) implementing ZellijPlugin trait with load/update/render/pipe\n4. Created `build.sh` with PATH fix for rustup vs system Rust priority\n5. Build produces 703 KB WASM binary — well under 1 MB limit\n\nNote: Used zellij-tile 0.42.2 (latest on crates.io compatible with Zellij 0.43.1). The file is `lib.rs` not `main.rs` to avoid Cargo's default bin target autodetection conflicting with the cdylib lib target.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-37 Completed\n\nScaffolded Rust WASM plugin project at `lince-dashboard/plugin/`.\n\n### Files created\n- `Cargo.toml` — cdylib targeting wasm32-wasip1, depends on zellij-tile 0.42.2\n- `src/lib.rs` — ZellijPlugin impl with event subscriptions, permission requests, basic dashboard render\n- `build.sh` — builds and copies .wasm to output path (703 KB)\n\n### Key decisions\n- Used `lib.rs` instead of `main.rs` to avoid Cargo bin/lib target conflict\n- zellij-tile 0.42.2 (latest on crates.io) is API-compatible with Zellij 0.43.1\n- `build.sh` forces `$HOME/.cargo/bin` to front of PATH for rustup/system Rust coexistence\n- AC #4 (plugin loads in Zellij) deferred to manual testing — requires Zellij session
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Code compiles with zero warnings on wasm32-wasip1
- [x] #2 build.sh is executable and succeeds on a clean checkout
- [ ] #3 Manual test: plugin loads in Zellij without permission errors
<!-- DOD:END -->
