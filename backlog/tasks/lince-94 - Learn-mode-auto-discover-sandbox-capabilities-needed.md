---
id: LINCE-94
title: 'Learn mode: auto-discover sandbox capabilities needed'
status: Done
assignee: []
created_date: '2026-03-26 12:30'
updated_date: '2026-03-26 13:35'
labels:
  - sandbox
  - security
  - DX
  - feature
milestone: m-13
dependencies: []
references:
  - sandbox/docs/comparison-agent-sandbox-vs-nono.md
  - sandbox/agent-sandbox
  - sandbox/config.toml.example
  - sandbox/agents-defaults.toml
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Users currently configure the sandbox manually — writable dirs, read-only dirs, env vars. It's hard to know if the sandbox is too loose (security risk) or too tight (agent fails). There's no way to discover what the agent actually needs.

nono has a "learn mode" that uses `strace` (Linux) / `fs_usage` (macOS) to trace what the sandboxed process actually touches, then generates a profile.

## Implementation Plan

### Phase 1: Trace Collection
1. Add `agent-sandbox learn <agent>` command that runs the agent inside a permissive sandbox with `strace` attached.
2. Use `strace -f -e trace=openat,openat2,connect,bind,execve -o /tmp/trace.log -- bwrap ...` to capture filesystem and network access.
3. Parse the strace output to extract:
   - **File reads**: paths opened with O_RDONLY
   - **File writes**: paths opened with O_WRONLY, O_RDWR, O_CREAT
   - **Network connections**: connect() calls with IP/port
   - **Executables**: execve() calls
4. Normalize paths: resolve symlinks, collapse `/proc/self/`, group by directory prefix.

### Phase 2: Profile Generation
1. Categorize discovered paths into:
   - **Project files**: within CWD → already writable, no action needed
   - **Home config**: `~/.claude/`, `~/.config/` → suggest read-only or writable binding
   - **System paths**: `/usr/`, `/etc/` → already covered by read-only root
   - **Toolchain caches**: `~/.cargo/registry/`, `~/.npm/` → suggest writable cache binding
   - **Unexpected writes**: anything outside expected areas → flag for review
2. Generate a suggested config fragment (TOML) that the user can merge into their `config.toml`.
3. Compare suggested config vs current config and highlight:
   - Unnecessary permissions (currently allowed but never accessed)
   - Missing permissions (accessed but not currently allowed — would fail in strict mode)

### Phase 3: Report and UX
1. Print a human-readable report after the learn session:
   ```
   === Learn Mode Report ===
   Files read:     142 (12 unique directories)
   Files written:   23 (3 unique directories)
   Network:         4 connections (api.anthropic.com:443, pypi.org:443, ...)
   Executables:     8 binaries
   
   Suggested changes to config.toml:
   + [sandbox] extra_rw = ["/home/user/.cache/uv"]   # uv wrote cache files
   - [env] passthrough: UNUSED_VAR                     # never accessed
   ```
2. Add `--apply` flag to auto-merge suggestions into config.
3. Add `--duration <seconds>` to limit the learn session length.

### Phase 4: Comparison Mode
1. `agent-sandbox learn --compare` — run learn mode and compare against current config, showing over-permissive and under-permissive areas.
2. Useful for periodic sandbox tightening.

## Key Design Decisions
- **strace-based** — available on all Linux distros, no kernel version requirements, well-understood output format.
- **Permissive sandbox during learn** — the point is to discover what the agent needs, not to block it.
- **Suggest, don't auto-apply** — user reviews and approves changes.
- **Directory-level grouping** — report at directory level, not individual files (too noisy).
- **No persistent daemon** — learn mode is a one-shot session, not continuous monitoring.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agent-sandbox learn <agent> runs the agent with strace and captures file/network/exec access
- [ ] #2 Strace output is parsed into categorized access lists (reads, writes, network, executables)
- [ ] #3 A suggested config.toml fragment is generated based on observed access patterns
- [ ] #4 Report identifies unnecessary permissions (allowed but never used)
- [ ] #5 Report identifies missing permissions (accessed but not currently allowed)
- [ ] #6 Works with all configured agents (Claude, Codex, Gemini, etc.)
- [ ] #7 --duration flag limits the learn session to N seconds
- [ ] #8 --compare flag shows delta between current config and observed needs
- [ ] #9 Output is human-readable with clear suggested actions
- [ ] #10 strace is validated as available before starting (helpful error if missing)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented in sandbox/agent-sandbox:

- `StraceParser` class (line 2644): Parses strace output for openat/openat2, connect, execve syscalls. Categorizes paths into project/home_config/system/toolchain/temp/unexpected. Resolves IPs to hostnames with caching.
- `generate_config_suggestions()`: Compares observed access vs current config, identifies missing and unnecessary permissions, generates TOML fragment
- `print_learn_report()`: Human-readable report with filesystem access summary, network connections, executables, and suggested config changes
- `build_learn_bwrap_cmd()`: Builds permissive bwrap command with writable home for access pattern discovery
- `cmd_learn()` (line 3351): Orchestrates strace wrapping, trace parsing, suggestion generation, and optional --apply
- Supports --duration (timeout), --compare (delta vs current config), --apply (auto-merge), --output (save TOML)
- Validates strace availability before starting
<!-- SECTION:NOTES:END -->
