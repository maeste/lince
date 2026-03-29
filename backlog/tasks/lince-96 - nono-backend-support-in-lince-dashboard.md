---
id: LINCE-96
title: nono backend support in lince-dashboard
status: Done
assignee: []
created_date: '2026-03-26 12:31'
updated_date: '2026-03-26 19:19'
labels:
  - lince-dashboard
  - sandbox
  - nono
  - feature
milestone: m-13
dependencies:
  - LINCE-95
references:
  - sandbox/docs/comparison-agent-sandbox-vs-nono.md
  - 'https://github.com/always-further/nono'
  - lince-dashboard/plugin/src/
  - sandbox/agent-sandbox
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

lince-dashboard currently only supports agent-sandbox (bubblewrap) as the sandbox backend for launching agents. Users who prefer nono's Landlock-based isolation (or who are on systems where nono is already installed) cannot use it from the dashboard.

**Critically, macOS users cannot use lince-dashboard for sandboxed agent execution at all**, since agent-sandbox is Linux-only. Adding nono support makes the dashboard usable on macOS.

## Implementation Plan

### Phase 1: Backend Abstraction Layer
1. In `lince-dashboard`, create a sandbox backend trait/abstraction:
   ```
   SandboxBackend {
     name: String           // "agent-sandbox" | "nono"
     detect() -> bool       // is the backend available on this system?
     build_command(agent, project_dir, profile) -> Command
     status() -> SandboxStatus
     supports_feature(feature) -> bool  // rollback, proxy, learn, etc.
   }
   ```
2. Refactor existing agent-sandbox launch logic to implement this trait.
3. Implement nono backend:
   - `detect()`: check if `nono` binary is in `$PATH`
   - `build_command()`: construct `nono run --profile <agent> -- <agent_command>` with appropriate flags
   - Map lince agent config to nono profile names (see dependency: LINCE-95)

### Phase 2: Configuration
1. Add `[dashboard] sandbox_backend = "agent-sandbox" | "nono" | "auto"` to lince config.
2. `auto` mode: on Linux prefer agent-sandbox if available, fall back to nono. On macOS use nono (agent-sandbox is not an option). Error if no backend available.
3. Per-agent override: `[agents.claude] sandbox_backend = "nono"` — allows mixing backends on Linux.

### Phase 3: Dashboard UI Integration
1. Show active sandbox backend in the agent status panel (e.g., "bwrap" or "nono").
2. If nono is used and supports rollback, show a rollback action in the agent panel.
3. If nono's `why` command is available, integrate it into a diagnostic view.
4. On macOS, never show agent-sandbox as an option — only nono.

### Phase 4: Feature Parity Mapping
1. Map equivalent features between backends:
   | Feature | agent-sandbox | nono |
   |---------|--------------|------|
   | Launch agent | `agent-sandbox run -a X` | `nono run --profile X -- cmd` |
   | Config diff | `agent-sandbox diff` | N/A |
   | Rollback | N/A (unless snapshot task done) | `nono undo` |
   | Status | `agent-sandbox status` | `nono why <path>` |
   | Learn | N/A (unless learn task done) | `nono learn` |
2. Dashboard gracefully handles features not available in the active backend (disabled buttons/hidden panels).

### Phase 5: Install/Update/Uninstall Script Updates
1. **lince-dashboard install.sh**:
   - Detect OS. On macOS: check for nono, guide user to `brew install nono` if missing.
   - On Linux: check for agent-sandbox and/or nono, configure backend accordingly.
   - Set default `sandbox_backend` in dashboard config based on detected backends and OS.
2. **lince-dashboard update.sh**:
   - Verify configured backend is still available after update.
   - On macOS: check nono version, notify if outdated.
3. **lince-dashboard uninstall.sh**:
   - Clean up dashboard-specific backend config. Do NOT remove agent-sandbox or nono themselves.

### Phase 6: Documentation Updates
1. **lince-dashboard README.md**:
   - Prerequisites section must list sandbox backend requirements per OS:
     - Linux: agent-sandbox (recommended) or nono
     - macOS: nono (required) — "agent-sandbox is Linux-only; nono is the supported sandbox on macOS"
   - Installation section covers both OS paths.
2. **Quickstart / Getting Started**:
   - Linux: `install agent-sandbox` → `install lince-dashboard` → works
   - macOS: `brew install nono` → `install lince-dashboard` → auto-detects nono → works
3. **User guide**:
   - How to switch backends
   - Per-agent backend override
   - Feature comparison (what's available with each backend)
   - Troubleshooting: "No sandbox backend found" errors per OS
4. **CLAUDE.md** project instructions: mention that dashboard supports both backends and macOS requires nono.

## Key Design Decisions
- **Abstraction, not replacement** — both backends coexist; user chooses (or auto on Linux, nono-only on macOS).
- **Auto-detection is OS-aware** — macOS auto mode always picks nono; Linux prefers agent-sandbox.
- **Per-agent backend** — power users on Linux can use nono for some agents and bwrap for others.
- **Graceful degradation** — features not supported by a backend are hidden, not errored.
- **No nono configuration management** — we don't manage nono profiles, just invoke them. nono profile setup is the user's responsibility (or via LINCE-95 nono-sync).
- **macOS is a first-class path** — not an afterthought; docs and scripts treat it as a primary setup path via nono.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Dashboard can launch agents using nono as sandbox backend when nono is installed
- [ ] #2 Dashboard can launch agents using agent-sandbox as before (no regression)
- [ ] #3 auto mode on Linux detects available backends and prefers agent-sandbox
- [ ] #4 auto mode on macOS uses nono exclusively (agent-sandbox is never offered)
- [ ] #5 Per-agent sandbox_backend override works correctly
- [ ] #6 Dashboard UI shows which backend is active for each agent
- [ ] #7 Features not supported by a backend are gracefully hidden (not errored)
- [ ] #8 nono rollback (undo) is accessible from dashboard when nono backend is active
- [ ] #9 Backend abstraction layer is clean enough to add future backends
- [ ] #10 lince-dashboard install.sh detects OS and guides macOS users to install nono
- [ ] #11 lince-dashboard install.sh sets correct default backend per OS in config
- [ ] #12 lince-dashboard README.md lists sandbox prerequisites per OS (Linux: agent-sandbox or nono, macOS: nono required)
- [ ] #13 Quickstart documentation covers both Linux and macOS setup paths
- [ ] #14 User guide documents backend switching, per-agent override, and feature comparison
- [ ] #15 Clear error message when no sandbox backend is available, with OS-specific install guidance
- [ ] #16 Integration tests cover both backends (or mock nono if not installed)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Summary

### Rust code (lince-dashboard/plugin/src/)
- `sandbox_backend.rs`: Complete module with `SandboxBackend` enum (AgentSandbox, Nono, None), `BackendConfig` enum (Auto, AgentSandbox, Nono), `SandboxFeature` enum, `DetectedBackends` struct with async detection and OS-aware resolution (macOS always picks nono, Linux prefers agent-sandbox).
- `config.rs`: `DashboardConfig.sandbox_backend: BackendConfig` for global default. `AgentTypeConfig.sandbox_backend: SandboxBackend` for per-agent override.
- `dashboard.rs`: Shows backend display name in agent detail panel and table.
- `main.rs`: Calls `detect_backend_async()` on load, handles `CMD_DETECT_BACKEND` result.
- `agent.rs`: Suffix stripping supports `-nono` variant types.

### Install scripts
- `install.sh`: Post-install sandbox backend check. Detects OS, checks for agent-sandbox and nono, provides macOS-specific guidance (`brew install nono`).
- `update.sh`: Already had sandbox config check (unchanged, nono detection covered by dashboard auto-detect).
- `uninstall.sh`: No nono-specific cleanup needed (dashboard doesn't manage nono profiles).

### Documentation
- `README.md`: Updated prerequisites (sandbox backend per OS). New "Sandbox Backends" section with config, macOS setup, per-agent override, feature comparison table. Updated overview paragraph.
<!-- SECTION:NOTES:END -->
