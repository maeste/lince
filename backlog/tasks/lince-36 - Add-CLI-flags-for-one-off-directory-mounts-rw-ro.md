---
id: LINCE-36
title: 'Add CLI flags for one-off directory mounts (--rw, --ro)'
status: Done
assignee: []
created_date: '2026-03-11 10:36'
updated_date: '2026-03-12 08:18'
labels:
  - sandbox
  - cli
  - enhancement
dependencies: []
references:
  - sandbox/claude-sandbox
  - sandbox/config.toml.example
  - sandbox/README.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context

The sandbox already supports persistent RW/RO directory mounts via `config.toml`:
- `[sandbox].extra_rw` — list of read-write directories
- `[sandbox].ro_dirs` — list of read-only directories
- `[sandbox].home_ro_dirs` — relative home subdirectories (read-only)

However, there is **no CLI mechanism** for one-off mounts during a single `run` invocation. Users must edit `config.toml` to add a temporary directory, then remove it after. This is inconvenient for ad-hoc needs like mounting a data directory or a shared library path for a single session.

## Usage Examples

```bash
# Single read-write mount
claude-sandbox run --rw /mnt/data

# Multiple mounts of different types
claude-sandbox run --rw /mnt/data --rw ~/shared-libs --ro /opt/datasets

# Combined with other flags and Claude args
claude-sandbox run --rw /mnt/data --ro /opt/reference -P vertex -- --model sonnet

# Dry-run to verify mount points
claude-sandbox run --dry-run --rw /tmp/test --ro /opt/ref
```

## Implementation Plan

**File**: `sandbox/claude-sandbox` (single file, 5 change locations)

### Step 1: Add CLI argument definitions (~line 881, after `--dry-run`)

```python
p_run.add_argument("--rw", action="append", default=[],
                   metavar="DIR", help="Extra read-write directory for this run (repeatable)")
p_run.add_argument("--ro", action="append", default=[],
                   metavar="DIR", help="Extra read-only directory for this run (repeatable)")
```

### Step 2: Extend `build_bwrap_cmd()` signature (~line 184)

Add two optional parameters:

```python
def build_bwrap_cmd(config: dict, project_dir: Path,
                    claude_args: list[str],
                    log_file: Path | None = None,
                    profile: str | None = None,
                    safe_mode: bool = False,
                    extra_rw_cli: list[str] | None = None,
                    extra_ro_cli: list[str] | None = None) -> list[str]:
```

### Step 3: Mount CLI directories in `build_bwrap_cmd()` (after section 10, ~line 310)

Insert after the config-based `extra_rw` loop:

```python
# --- 10b. CLI extra read-only dirs -----------------------------------------
for d in (extra_ro_cli or []):
    ep = str(expand(d))
    if os.path.isdir(ep):
        cmd += ["--ro-bind", ep, ep]
    else:
        print(f"Warning: --ro directory does not exist, skipping: {d}", file=sys.stderr)

# --- 10c. CLI extra read-write dirs ----------------------------------------
for d in (extra_rw_cli or []):
    ep = str(expand(d))
    if os.path.isdir(ep):
        cmd += ["--bind", ep, ep]
    else:
        print(f"Warning: --rw directory does not exist, skipping: {d}", file=sys.stderr)
```

RW mounts go last so they override any earlier RO mount on the same path.

### Step 4: Pass CLI args from `cmd_run()` to `build_bwrap_cmd()` (~line 550)

```python
cmd = build_bwrap_cmd(config, project_dir, claude_extra, log_file,
                      profile=profile, safe_mode=args.safe,
                      extra_rw_cli=args.rw, extra_ro_cli=args.ro)
```

### Step 5: Show CLI mounts in the startup banner (~line 576)

```python
if args.rw:
    print(f"  extra rw    {', '.join(args.rw)}")
if args.ro:
    print(f"  extra ro    {', '.join(args.ro)}")
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 --rw DIR flag accepted by run subcommand, repeatable via multiple --rw flags
- [x] #2 --ro DIR flag accepted by run subcommand, repeatable via multiple --ro flags
- [x] #3 --rw directories appear as --bind DIR DIR in the bwrap command
- [x] #4 --ro directories appear as --ro-bind DIR DIR in the bwrap command
- [x] #5 Tilde expansion works: --rw ~/data resolves to absolute path
- [x] #6 Non-existent directories produce a warning on stderr and are skipped (not a fatal error)
- [x] #7 --dry-run output includes CLI-specified mounts in the printed bwrap command
- [x] #8 Startup banner displays CLI mounts when specified
- [x] #9 No behavioral change when flags are not used (backward compatible)
- [x] #10 CLI mounts coexist with config-based extra_rw and ro_dirs (both applied)
- [x] #11 CLI mounts are applied after config mounts (CLI can override config for same path)
- [x] #12 Unknown flags before -- still pass through to Claude CLI (existing behavior preserved)
- [x] #13 --help shows the new flags with clear descriptions
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation completed 2026-03-12. All 5 steps from the plan applied to sandbox/claude-sandbox:
1. Added --rw/--ro CLI args (argparse append action)
2. Extended build_bwrap_cmd() signature with extra_rw_cli/extra_ro_cli
3. Added mount logic after config-based extra_rw (RO first, then RW for override)
4. Passed args.rw/args.ro from cmd_run() to build_bwrap_cmd()
5. Added banner output for CLI mounts

Syntax verified with py_compile. --help output confirmed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Summary\n\nAdded `--rw DIR` and `--ro DIR` CLI flags to the `run` subcommand, allowing one-off directory mounts without editing `config.toml`.\n\n## Changes\n\n**File**: `sandbox/claude-sandbox` (5 locations)\n\n- **CLI args**: Added `--rw` and `--ro` as repeatable `append` arguments after `--dry-run`\n- **Function signature**: Extended `build_bwrap_cmd()` with `extra_rw_cli` and `extra_ro_cli` optional params\n- **Mount logic**: CLI RO dirs mounted as `--ro-bind`, CLI RW dirs as `--bind`, applied after config mounts (RW last to allow override). Non-existent dirs produce stderr warning and are skipped.\n- **Caller wiring**: `cmd_run()` passes `args.rw`/`args.ro` to `build_bwrap_cmd()`\n- **Banner**: Startup banner shows `extra rw` and `extra ro` lines when flags are used\n\n## Testing\n\n- Python syntax check passed (`py_compile`)\n- `--help` output confirmed both flags with descriptions\n- Backward compatible: no behavior change when flags not used (defaults to empty list)
<!-- SECTION:FINAL_SUMMARY:END -->
