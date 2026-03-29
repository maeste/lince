---
id: LINCE-95
title: nono profile compatibility mapping for lince agents
status: Done
assignee: []
created_date: '2026-03-26 12:31'
updated_date: '2026-03-26 19:19'
labels:
  - sandbox
  - nono
  - config
  - feature
milestone: m-13
dependencies: []
references:
  - sandbox/agents-defaults.toml
  - sandbox/config.toml.example
  - 'https://github.com/always-further/nono (profile system)'
  - sandbox/docs/comparison-agent-sandbox-vs-nono.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

lince uses its own agent configuration format (`agents-defaults.toml` + `config.toml`) while nono uses JSON profiles (`~/.config/nono/profiles/`). For nono to work as a backend in lince-dashboard, we need a way to bridge these two configuration systems.

Additionally, nono is the only supported sandbox option for macOS users, since agent-sandbox is Linux-only (bubblewrap depends on Linux namespaces). Documentation and install scripts must make this clear.

## Implementation Plan

### Phase 1: Profile Mapping Spec
1. Document the mapping between lince agent config fields and nono profile fields:
   | lince config | nono profile |
   |-------------|-------------|
   | `[agents.<name>].command` | Profile's executable target |
   | `[agents.<name>].args` | Arguments passed after `--` |
   | `[agents.<name>].env` | `secrets.env_mappings` or nono env config |
   | `[env].passthrough` | nono's environment passthrough |
   | `[sandbox].extra_rw` | `filesystem.write` |
   | `[sandbox].extra_ro` | `filesystem.read` |
   | `[security].block_git_push` | `security.allowed_commands` (exclude git push) |
   | `[agents.<name>.profiles.<p>]` | nono `secrets` config |
2. Identify gaps — features in one system that have no equivalent in the other.

### Phase 2: Translation Layer
1. Create a Python utility (`sandbox/nono-profile-gen`) that reads lince config and generates nono JSON profiles.
2. Generate profiles in `~/.config/nono/profiles/lince-<agent>.json`.
3. Handle the translation with sensible defaults for nono fields that have no lince equivalent (e.g., nono's `destructive_commands` deny list).
4. Support `--dry-run` to show what would be generated without writing files.

### Phase 3: Sync and Validation
1. `agent-sandbox nono-sync` command: regenerate nono profiles from current lince config.
2. Validate generated profiles by running `nono why` against expected paths (if nono is installed).
3. Warn about features that don't translate (e.g., lince's bwrap_conflict handling has no nono equivalent).

### Phase 4: Install/Update/Uninstall Script Updates
1. **install.sh**:
   - Detect OS: Linux vs macOS.
   - On Linux: install agent-sandbox as before. Optionally offer nono as alternative if kernel >= 5.13.
   - On macOS: skip agent-sandbox entirely (bwrap not available). Check if nono is installed (`command -v nono`). If not, print clear guidance: "agent-sandbox requires Linux. On macOS, install nono: `brew install nono`" with a link to the nono project.
   - When nono is detected (any OS): run `nono-profile-gen` to generate lince-compatible profiles.
   - Add a `[sandbox] backend = "agent-sandbox" | "nono" | "auto"` entry to the generated config.toml, defaulting to `"auto"`.
2. **update.sh**:
   - Re-run `nono-profile-gen` if nono is installed (profiles may need updating after config changes).
   - On macOS: check for nono updates via `brew outdated nono` and notify user.
   - Update agents-defaults.toml as before.
3. **uninstall.sh**:
   - Offer to remove generated nono profiles (`~/.config/nono/profiles/lince-*.json`).
   - Do NOT uninstall nono itself (user may use it independently).
   - Clean up any lince-specific nono config.

### Phase 5: Documentation
1. **sandbox/README.md** — add a "Sandbox Backends" section:
   - agent-sandbox (Linux, bubblewrap-based) — default on Linux
   - nono (Linux + macOS, Landlock/Seatbelt-based) — required on macOS, optional on Linux
   - Feature comparison table (what each backend supports)
   - Clear statement: "**macOS users**: agent-sandbox is Linux-only. Use nono as your sandbox backend."
2. **sandbox/docs/nono-integration.md** — detailed integration guide:
   - Profile mapping reference table
   - How `nono-profile-gen` works
   - Manual nono profile creation for advanced users
   - Known limitations and features that don't translate
   - Troubleshooting common issues
3. **Quickstart guide** (sandbox/docs/quickstart.md or section in README):
   - Linux quickstart: `./install.sh` → ready to go
   - macOS quickstart: `brew install nono` → `./install.sh` → detects nono → generates profiles → ready to go
   - How to switch backends: edit `config.toml` `[sandbox] backend = "nono"`
   - How to verify: `agent-sandbox status` shows active backend
4. **User guide updates** — any existing user-facing docs that mention sandbox setup must include the nono alternative and macOS guidance.

### Phase 6: Config and UX
1. `agent-sandbox status` — show detected backends and which is active.
2. If on macOS and nono is not installed, `agent-sandbox run` should print a clear error: "agent-sandbox requires Linux namespaces (bubblewrap). On macOS, install nono: `brew install nono` and set `backend = nono` in config.toml."
3. `agent-sandbox doctor` (or extend `status`) — validate that the active backend is properly configured.

## Key Design Decisions
- **One-way generation** — lince config is source of truth, nono profiles are generated.
- **Prefix naming** — generated profiles use `lince-` prefix to avoid conflicting with user's own nono profiles.
- **No runtime translation** — profiles are generated ahead of time, not on-the-fly.
- **Conservative defaults** — when a lince config has no nono equivalent, use the more restrictive option.
- **macOS = nono** — agent-sandbox cannot work on macOS; nono is the only option there. This must be clear in all docs and error messages.
- **Install scripts are the entry point** — users shouldn't need to manually configure nono integration; install.sh handles detection and setup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Mapping between lince config fields and nono profile fields is documented
- [ ] #2 Python utility generates valid nono JSON profiles from lince agent config
- [ ] #3 Generated profiles work correctly with nono run --profile lince-<agent>
- [ ] #4 --dry-run flag shows generated profile without writing to disk
- [ ] #5 agent-sandbox nono-sync regenerates all nono profiles from current config
- [ ] #6 Untranslatable features produce clear warnings (not silent omissions)
- [ ] #7 Generated profiles use lince- prefix to avoid naming conflicts
- [ ] #8 install.sh detects OS and guides macOS users to install nono with clear messaging
- [ ] #9 install.sh on macOS skips bwrap setup entirely and configures nono backend
- [ ] #10 install.sh runs nono-profile-gen when nono is detected (any OS)
- [ ] #11 update.sh re-runs nono-profile-gen if nono is installed
- [ ] #12 uninstall.sh offers to remove generated lince-* nono profiles without uninstalling nono itself
- [ ] #13 sandbox/README.md has a Sandbox Backends section with feature comparison and macOS guidance
- [ ] #14 sandbox/docs/nono-integration.md covers profile mapping, nono-profile-gen usage, and troubleshooting
- [ ] #15 Quickstart documentation covers both Linux (agent-sandbox) and macOS (nono) setup paths
- [ ] #16 agent-sandbox run on macOS prints a clear error directing user to install nono
- [ ] #17 agent-sandbox status shows detected backends and which is active
- [ ] #18 Works for all shipped agents (claude, codex, gemini, aider, opencode, amp)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Summary

### agent-sandbox code (sandbox/agent-sandbox)
- `detect_backends()` (line 782): Detects available sandbox backends (bwrap, nono) via `shutil.which()`
- `build_nono_cmd()` (line 842): Builds `nono run --profile lince-<agent> -- <cmd> <args>` command
- `cmd_nono_sync()` (line 1010): Generates nono JSON profiles from lince config. Maps agent config fields to nono profile format. Supports `--dry-run`, `--agent`, `--profile`. Warns about untranslatable features (bwrap_conflict, snapshot settings).
- Backend config: `[sandbox] backend = "auto" | "agent-sandbox" | "nono"` in config.toml
- `cmd_status()` updated to show detected backends and active backend
- `cmd_run()` routes to `build_nono_cmd()` or `build_bwrap_cmd()` based on backend

### Install scripts
- `install.sh`: OS detection (Linux/macOS). macOS skips bwrap, requires nono with clear guidance. Runs `nono-sync` when nono detected. Shows backend info in summary.
- `update.sh`: Re-runs `nono-sync` if nono installed. Checks `brew outdated nono` on macOS.
- `uninstall.sh`: Offers to remove generated `lince-*.json` nono profiles. Does NOT uninstall nono itself.

### Documentation
- `sandbox/docs/nono-integration.md`: Full guide — setup, profile mapping reference, feature comparison, troubleshooting
- `sandbox/README.md`: New "Sandbox Backends" section with comparison table, backend switching, macOS guidance. Updated Requirements section with Linux/macOS subsections.
<!-- SECTION:NOTES:END -->
