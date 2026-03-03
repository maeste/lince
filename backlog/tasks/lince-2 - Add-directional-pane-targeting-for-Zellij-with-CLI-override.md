---
id: LINCE-2
title: Add directional pane targeting for Zellij with CLI override
status: Done
assignee: []
created_date: '2026-03-03 12:33'
updated_date: '2026-03-03 12:36'
labels:
  - voxcode
  - feature
  - zellij
dependencies: []
references:
  - voxcode/src/voxcode/zellij_bridge.py
  - voxcode/src/voxcode/config.py
  - voxcode/src/voxcode/cli.py
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Improve Zellij pane targeting in voxcode by supporting directional navigation (`left`, `right`, `up`, `down`) in addition to the current `next`/`previous`, and add a `--target-pane` CLI argument that takes priority over the config file.

**Problem:**
Currently `ZellijBridge` only supports `next`/`previous` pane cycling via `zellij action focus-next-pane`. This breaks in layouts with 3+ panes because `next` doesn't guarantee reaching the intended pane. Zellij's CLI has no way to target a pane by name or ID (open feature request zellij-org/zellij#3061), but it does support `zellij action move-focus <direction>` which is deterministic based on layout position.

**Current state:**
- `ZellijConfig.target_pane` accepts `""`, `"next"`, or `"previous"` (config.py:62)
- `ZellijBridge.get_target_pane()` returns `"next"` by default (zellij_bridge.py:36-44)
- `ZellijBridge.send_text()` uses `zellij action focus-{direction}-pane` (zellij_bridge.py:56-59)
- No CLI argument exists for target pane — only `--backend` for multiplexer selection
- CLI override pattern already established: `--mode`, `--model`, `--device` etc. all override config (cli.py:418-427)

**Desired behavior:**
- Config: `[zellij] target_pane = "right"` (or left/up/down/next/previous)
- CLI: `voxcode --target-pane right` overrides any config value
- CLI takes priority over config file
- Directional values use `zellij action move-focus <direction>` 
- Legacy `next`/`previous` still use `zellij action focus-{next,previous}-pane`

**Key files:**
- `voxcode/src/voxcode/zellij_bridge.py` — `ZellijBridge`, `get_target_pane()`, `send_text()`
- `voxcode/src/voxcode/config.py` — `ZellijConfig` dataclass
- `voxcode/src/voxcode/cli.py` — argparse setup (line 370-387), CLI-to-config override (line 418-427)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ZellijConfig.target_pane accepts directional values: left, right, up, down (in addition to existing next, previous)
- [x] #2 Directional values use `zellij action move-focus <direction>` instead of `focus-{next,previous}-pane`
- [x] #3 Legacy next/previous values continue to work with existing focus-next-pane/focus-previous-pane commands
- [x] #4 New --target-pane CLI argument accepts all valid values: left, right, up, down, next, previous
- [x] #5 --target-pane CLI argument overrides [zellij] target_pane from config.toml
- [x] #6 Default behavior (no config, no CLI arg) remains "next" for backward compatibility
- [x] #7 Invalid target_pane values are rejected with a clear error message at startup
- [x] #8 Return-to-voxcode after send_enter=true uses the correct opposite direction (e.g. right→left, up→down)
- [x] #9 UI displays the resolved target direction on startup (e.g. "target: right")
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Define valid directions and opposite mapping in zellij_bridge.py

Add constants at module level:
```python
DIRECTIONAL_TARGETS = {"left", "right", "up", "down"}
CYCLE_TARGETS = {"next", "previous"}
VALID_TARGETS = DIRECTIONAL_TARGETS | CYCLE_TARGETS

OPPOSITE_DIRECTION = {
    "left": "right", "right": "left",
    "up": "down", "down": "up",
    "next": "previous", "previous": "next",
}
```

### Step 2: Update ZellijBridge.send_text() for directional navigation

Currently uses `zellij action focus-{direction}-pane` for all values. Change to:
- If direction in `DIRECTIONAL_TARGETS`: use `zellij action move-focus <direction>`
- If direction in `CYCLE_TARGETS`: use `zellij action focus-{direction}-pane` (existing behavior)

The return-focus logic (when `send_enter=True`) must use `OPPOSITE_DIRECTION` map:
- `right` → return with `move-focus left`
- `next` → return with `focus-previous-pane`

### Step 3: Add validation in ZellijBridge.__init__ or validate()

Validate `target_pane` against `VALID_TARGETS` (plus empty string for default). Raise `RuntimeError` with a clear message listing valid options if invalid.

### Step 4: Add --target-pane CLI argument in cli.py

In `main()` argparse setup (after line 386):
```python
parser.add_argument(
    "--target-pane",
    choices=["left", "right", "up", "down", "next", "previous"],
    help="Target pane direction for Zellij (overrides config)",
)
```

### Step 5: Apply CLI override in cli.py

In the CLI-to-config override block (after line 427):
```python
if args.target_pane:
    config.zellij.target_pane = args.target_pane
```

This follows the existing pattern where CLI args mutate the config object before passing it to VoxCode.

### Step 6: Update config.toml example

```toml
[zellij]
# Target pane direction: left, right, up, down, next, previous
# "next" (default) cycles to the next pane — works for 2-pane layouts
# Directional values are more reliable for 3+ pane layouts
target_pane = "right"
```

### Step 7: Verify UI displays target direction

In `cli.py:58-60`, `self.ui.target_pane = target` already displays the resolved pane target. The directional value will flow through naturally since `get_target_pane()` returns the string. Verify it renders correctly in the UI.

### Estimated effort: Small-Medium (1-2 hours)
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Changes

### `voxcode/src/voxcode/zellij_bridge.py`
- Added module-level constants: `DIRECTIONAL_TARGETS`, `CYCLE_TARGETS`, `VALID_TARGETS`, `OPPOSITE_DIRECTION` mapping
- Added `_focus_pane(direction)` helper: uses `move-focus <dir>` for directional targets, `focus-{dir}-pane` for cycle targets
- Updated `validate()`: rejects invalid `target_pane` values with clear error listing all valid options
- Updated `send_text()`: uses `OPPOSITE_DIRECTION` map and `_focus_pane()` for both focus and return-focus

### `voxcode/src/voxcode/config.py`
- Updated `ZellijConfig.target_pane` comment to document all valid values

### `voxcode/src/voxcode/cli.py`
- Added `--target-pane` CLI argument with choices: left, right, up, down, next, previous
- Added CLI-to-config override: `args.target_pane` sets `config.zellij.target_pane`

### `voxcode/config.toml`
- Added `[zellij]` section with documented `target_pane` option (commented out, default next)
- Added `[multiplexer]` section placeholder
<!-- SECTION:FINAL_SUMMARY:END -->
