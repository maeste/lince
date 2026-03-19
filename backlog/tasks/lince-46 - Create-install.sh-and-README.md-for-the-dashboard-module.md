---
id: LINCE-46
title: Create install.sh and README.md for the dashboard module
status: To Do
assignee: []
created_date: '2026-03-19 10:40'
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
- [ ] #1 install.sh exists, is executable, handles all 9 installation steps
- [ ] #2 README.md exists with overview, prerequisites, installation, config reference, usage, architecture, troubleshooting
- [ ] #3 Root README.md updated with dashboard module reference under Modules section
- [ ] #4 Installer checks prerequisites before building
- [ ] #5 Installer is idempotent and backs up existing files
- [ ] #6 README includes keybinding table and configuration reference
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 install.sh passes shellcheck
- [ ] #2 Installer tested on clean system and system with existing install
- [ ] #3 README renders correctly as GitHub markdown
- [ ] #4 Root README module list consistent with actual directory structure
<!-- DOD:END -->
