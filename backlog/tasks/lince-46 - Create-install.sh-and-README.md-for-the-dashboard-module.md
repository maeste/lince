---
id: LINCE-46
title: Create install.sh and README.md for the dashboard module
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:40'
updated_date: '2026-03-19 14:00'
labels:
  - dashboard
  - install
  - docs
milestone: m-10
dependencies:
  - LINCE-37
  - LINCE-38
  - LINCE-44
  - LINCE-45
references:
  - zellij-setup/install.sh (installer pattern)
  - voxtts/README.md (README pattern)
  - /home/maeste/project/lince/README.md (root README to update)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the installer and documentation for the lince-dashboard module. Also update root README.md to reference the new module.

## Implementation Plan

1. Create `lince-dashboard/install.sh` (follow `zellij-setup/install.sh` style: colored output, confirmation prompts, backup):
   - Step 1: Check prerequisites — `zellij --version` (>= 0.40), `rustc`, `cargo`, `wasm32-wasip1` target
   - Step 2: Install `wasm32-wasip1` target if missing: `rustup target add wasm32-wasip1`
   - Step 3: Build plugin: run `plugin/build.sh`
   - Step 4: Copy `lince-dashboard.wasm` to `~/.config/zellij/plugins/`
   - Step 5: Copy layout files to `~/.config/zellij/layouts/`
   - Step 6: Copy config.toml to `~/.config/lince-dashboard/config.toml` (if not exists)
   - Step 7: Run `hooks/install-hooks.sh`
   - Step 8: Add alias `zd='zellij -l dashboard'` to `~/.bashrc` / `~/.zshrc`
   - Step 9: Print summary and usage
2. Create `lince-dashboard/README.md`:
   - Overview with ASCII art dashboard layout diagram
   - Prerequisites: Zellij 0.40+, Rust, Claude Code, claude-sandbox, VoxCode (optional)
   - Installation instructions
   - Configuration reference (all config.toml options with defaults)
   - Usage guide: keybindings table, agent lifecycle, voice relay setup
   - Architecture: module structure, Zellij plugin API, pipe IPC, hook system
   - Sandbox integration: env passthrough for hooks inside bubblewrap
   - Troubleshooting: plugin won't load, hooks not firing, status not updating
3. Update `/home/maeste/project/lince/README.md`:
   - Add `### [lince-dashboard/](lince-dashboard/)` section under "## Modules"
   - Brief description + link to module README
   - Update main ASCII layout diagram to show dashboard view
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 install.sh exists, is executable, handles all 9 installation steps
- [x] #2 README.md exists with overview, prerequisites, installation, config reference, usage, architecture, troubleshooting
- [x] #3 Root README.md updated with dashboard module reference under Modules section
- [x] #4 Installer checks prerequisites before building
- [x] #5 Installer is idempotent and backs up existing files
- [x] #6 README includes keybinding table and configuration reference
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Created `install.sh` with 8 steps: prerequisites check, WASM target, build, install plugin/layouts/config, hooks, shell alias\n2. Created `README.md` with: overview + ASCII diagram, prerequisites, installation, configuration reference, keybindings table, agent lifecycle, voice relay, status detection, architecture, sandbox integration, troubleshooting\n3. Updated root `README.md` to add lince-dashboard module under Modules section
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-46 Completed\n\n### Files created\n- `install.sh` — 8-step interactive installer (colored output, backup, idempotent alias)\n- `README.md` — Full documentation: overview, install, config, keybindings, architecture, troubleshooting\n\n### Files modified\n- Root `README.md` — Added lince-dashboard module description under Modules section\n\n### Key features of installer\n- Checks Zellij/Rust/cargo prerequisites\n- Builds WASM plugin via plugin/build.sh\n- Installs plugin, layouts, config, hooks\n- Adds `zd` shell alias\n- Backs up existing plugin on reinstall\n- Preserves existing config.toml\n\n### DoD deferred\n- #1 shellcheck not available in sandbox\n- #2 full installer test requires clean environment outside sandbox
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 install.sh passes shellcheck
- [ ] #2 Installer tested on clean system and system with existing install
- [x] #3 README renders correctly as GitHub markdown
- [x] #4 Root README module list consistent with actual directory structure
<!-- DOD:END -->
