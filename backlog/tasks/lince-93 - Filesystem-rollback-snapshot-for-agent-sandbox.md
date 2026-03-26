---
id: LINCE-93
title: Filesystem rollback / snapshot for agent-sandbox
status: Done
assignee: []
created_date: '2026-03-26 12:30'
updated_date: '2026-03-26 13:35'
labels:
  - sandbox
  - safety
  - feature
milestone: m-13
dependencies: []
references:
  - sandbox/docs/comparison-agent-sandbox-vs-nono.md
  - sandbox/agent-sandbox
  - sandbox/config.toml.example
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

When the agent damages files inside writable directories, recovery options are limited:
- **Project directory**: `git checkout` / `git stash` works for tracked files, but not for untracked files, binary artifacts, or non-git-tracked configs. Useless if the user hasn't committed recently.
- **Agent config directory**: The sandboxed copy (`~/.agent-sandbox/claude-config/`, `~/.agent-sandbox/codex-config/`, etc.) or the real one (when `use_real_config=true`) can be corrupted. The existing `diff/merge` workflow covers deliberate changes, but not accidental corruption or unwanted bulk modifications.

nono provides content-addressable snapshots with SHA-256 dedup and Merkle trees. We don't need that level of sophistication — a simpler approach will serve our use case.

## Implementation Plan

### Phase 1: Refactor diff/merge into a reusable comparison engine
1. The current `diff` and `merge` commands in agent-sandbox compare sandboxed config vs real config using `difflib` and an interactive file-by-file review loop. This logic is currently hardcoded to those two directories.
2. Extract the core comparison logic into reusable functions:
   ```python
   def compute_dir_diff(source_dir, target_dir, exclude=None) -> DirDiff:
       """Compare two directories, return list of (file, status, unified_diff)."""
       # status: created, modified, deleted, unchanged
   
   def interactive_review(diff: DirDiff, action="merge"|"restore") -> list[FileAction]:
       """Present diff to user, collect per-file accept/reject decisions."""
   
   def apply_actions(actions: list[FileAction], target_dir) -> None:
       """Apply accepted file actions (copy, delete, restore)."""
   ```
3. The existing `agent-sandbox diff` and `agent-sandbox merge` commands become thin wrappers:
   - `diff`: `compute_dir_diff(sandbox_config, real_config)` → print
   - `merge`: `compute_dir_diff(sandbox_config, real_config)` → `interactive_review` → `apply_actions`

### Phase 2: Snapshot Engine (rsync-based)
1. Before launching the sandbox, create lightweight snapshots of **both** the project directory and the agent config directory using `rsync --link-dest` (hardlink-based — near-zero disk cost for unchanged files).
2. Snapshot storage layout:
   ```
   ~/.agent-sandbox/snapshots/
   ├── projects/<project-hash>/<timestamp>/     # project dir snapshot
   └── configs/<agent-name>/<timestamp>/        # agent config snapshot
   ```
3. **Project dir**: Exclude large dirs by default: `.git/`, `node_modules/`, `target/`, `__pycache__/`, `.venv/`, `build/`, `dist/`. Configurable via `[snapshot] exclude = [...]`.
4. **Agent config dir**: Snapshot the entire directory (small, no exclusions needed). This covers:
   - Sandboxed copy: `~/.agent-sandbox/claude-config/`, `~/.agent-sandbox/codex-config/`, etc.
   - Real config (when `use_real_config=true`): `~/.claude/`, `~/.codex/`, etc.
   - Agent-specific settings, MCP configs, conversation history, memory files
5. Set a max snapshot count per target (default 3 for project, 5 for config), auto-prune oldest.

### Phase 3: Unified diff/snapshot commands
1. Reuse the comparison engine for all diff operations — the only difference is which two directories are compared:

   | Command | Source (left) | Target (right) | Purpose |
   |---------|--------------|----------------|---------|
   | `agent-sandbox diff` | sandbox config | real config | What did the agent change vs real? (existing) |
   | `agent-sandbox snapshot-diff <ts>` | snapshot | current dir | What changed since snapshot? |
   | `agent-sandbox snapshot-diff <ts1> <ts2>` | snapshot 1 | snapshot 2 | What changed between two sessions? |
   | `agent-sandbox merge` | sandbox config | real config | Apply agent changes to real (existing) |
   | `agent-sandbox snapshot-restore <ts>` | snapshot | current dir | Restore files from snapshot |

2. All commands use the same `compute_dir_diff` → `interactive_review` → `apply_actions` pipeline.
3. `snapshot-diff` with `--config` or `--project` selects which snapshot target to diff.
4. Cross-session comparison (`snapshot-diff <ts1> <ts2>`) lets users see what changed between two agent sessions — useful for understanding cumulative drift.

### Phase 4: Auto-Snapshot Integration
1. Add config options:
   ```toml
   [snapshot]
   auto_project = false    # snapshot project dir before each run
   auto_config = true      # snapshot agent config before each run (cheap, recommended)
   ```
2. Config snapshots are cheap (typically < 1MB) so default to `auto_config = true`.
3. Project snapshots default to `false` (can be slow for large repos).
4. On sandbox exit, print: "Session snapshots available. Run `agent-sandbox snapshot-diff` to review changes."

### Phase 5: Integration between diff/merge and snapshots
1. When restoring a config snapshot, warn if there are unmerged changes in the diff workflow (sandbox config diverged from real config).
2. `agent-sandbox diff --from-snapshot <ts>` — compare a config snapshot against the real config. This answers: "what would I be applying if I merged from this point in time?" Useful when the user wants to go back to a known-good state and re-merge from there.
3. `agent-sandbox status` shows both:
   - Snapshot info: last snapshot time, count, disk usage per type
   - Diff info: whether sandbox config has unmerged changes vs real config

### Phase 6: Cleanup and Maintenance
1. `agent-sandbox snapshot-prune [--config | --project | --all]` — manual cleanup.
2. `agent-sandbox snapshot-list` — list snapshots grouped by type (project/config) with timestamps and sizes.
3. Auto-prune on snapshot creation when exceeding max count.
4. Show disk usage in `agent-sandbox status` (per-type breakdown).

## Key Design Decisions
- **Reuse diff/merge engine** — snapshots feed into the same comparison pipeline as the existing diff/merge commands. One engine, multiple comparison pairs.
- **rsync + hardlinks** — simple, proven, near-zero cost for unchanged files. No custom storage engine.
- **Two snapshot targets** — project dir and agent config dir are independent; snapshotted and restored separately.
- **Config auto-snapshot on by default** — config dirs are small, corruption is hard to notice, and the diff/merge workflow doesn't protect against it.
- **Project auto-snapshot off by default** — can be slow for large repos; power users enable it.
- **Interactive restore** — never auto-restore; always show what will change and let user pick.
- **Cross-session diff** — comparing two snapshots reveals cumulative drift across multiple agent sessions.
- **Exclude large dirs** — project snapshots should be fast (< 5 seconds for typical projects).
- **Not a replacement for git** — this covers the gap between commits, not a VCS.
- **Not a replacement for diff/merge** — snapshot-restore is for undoing damage; diff/merge is for applying wanted changes. But they share the same engine.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Existing diff/merge logic is refactored into a reusable comparison engine (compute_dir_diff, interactive_review, apply_actions)
- [ ] #2 Existing agent-sandbox diff and agent-sandbox merge commands work exactly as before (no regression)
- [ ] #3 agent-sandbox snapshot creates hardlink-based snapshots of both project dir and agent config dir
- [ ] #4 agent-sandbox snapshot --config-only and --project-only flags work independently
- [ ] #5 Config snapshot covers the sandboxed copy (e.g., ~/.agent-sandbox/claude-config/) or real config dir when use_real_config=true
- [ ] #6 agent-sandbox snapshot-diff <ts> shows changes between snapshot and current state using the shared comparison engine
- [ ] #7 agent-sandbox snapshot-diff <ts1> <ts2> shows changes between two snapshots (cross-session comparison)
- [ ] #8 agent-sandbox snapshot-restore <ts> uses the same interactive_review UX as merge for per-file restoration
- [ ] #9 agent-sandbox diff --from-snapshot <ts> compares a config snapshot against the real config dir
- [ ] #10 agent-sandbox snapshot-list shows snapshots grouped by type (project/config) with timestamp and disk usage
- [ ] #11 Auto-snapshot for agent config is enabled by default (auto_config=true) and runs before each sandbox session
- [ ] #12 Auto-snapshot for project dir is opt-in (auto_project=false) and configurable
- [ ] #13 Large directories (.git, node_modules, target, etc.) are excluded from project snapshots by default
- [ ] #14 Max snapshot count is enforced per target type with automatic pruning of oldest
- [ ] #15 Snapshot storage uses hardlinks (rsync --link-dest) for minimal disk overhead
- [ ] #16 Restoring a config snapshot warns if there are unmerged changes in the diff/merge workflow
- [ ] #17 Works correctly with all configured agents (each has its own config snapshot namespace)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented in sandbox/agent-sandbox:

Phase 1 - Refactored diff/merge engine:
- `compute_dir_diff()` (line 1751): Generic two-directory comparison returning (path, status, diff_lines)
- `print_dir_diff()` (line 1828): Human-readable diff output
- `interactive_review()` (line 1851): Per-file accept/reject UX
- `apply_diff_actions()` (line 1912): Apply accepted changes
- `cmd_diff()` and `cmd_merge()` rewritten as thin wrappers

Phase 2 - Snapshot engine:
- `create_snapshot()` (line 2019): rsync --link-dest hardlink-based snapshots
- `list_snapshots()` (line 2070): Lists snapshots with timestamps and sizes
- `prune_snapshots()` (line 2093): Auto-prune oldest beyond max count

Phase 3 - Snapshot commands:
- `cmd_snapshot()`, `cmd_snapshot_list()`, `cmd_snapshot_diff()`, `cmd_snapshot_restore()`, `cmd_snapshot_prune()`
- Supports --config-only, --project-only flags and -a AGENT
- snapshot-diff supports two timestamps for cross-session comparison
- snapshot-restore uses same interactive_review UX as merge

Phase 4 - Auto-snapshot:
- Config: [snapshot] auto_project=false, auto_config=true
- Integrated into cmd_run() before bwrap launch

Phase 5 - Status integration:
- cmd_status() shows snapshot counts, sizes, and auto-snapshot config
<!-- SECTION:NOTES:END -->
