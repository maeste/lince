---
id: LINCE-103
title: 'claude: migrate to scratch_home_dirs and retire use_real_config'
status: To Do
assignee: []
created_date: '2026-05-05 18:13'
labels:
  - sandbox
  - refactor
  - follow-up
milestone: m-13
dependencies:
  - LINCE-99
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/58'
  - sandbox/agent-sandbox
  - sandbox/profiles/claude-paranoid.toml
  - sandbox/profiles/codex-paranoid.toml
documentation:
  - docs/documentation/dashboard/sandbox-levels.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Scope

Migrate the claude agent off its bespoke `[claude] use_real_config` mechanism onto the generic `scratch_home_dirs` mechanism introduced in LINCE-99. Two phases — Phase 1 is low-risk and self-contained; Phase 2 is a behavior change that wants an RFC first.

Tracks GH issue [#58](https://github.com/RisorseArtificiali/lince/issues/58).

## Background — what LINCE-99 shipped

LINCE-99 introduced a **generic ephemeral scratch mechanism** in `sandbox/agent-sandbox`: an agent-config field `scratch_home_dirs = [".codex"]` that makes `cmd_run` (bwrap path):

1. `tempfile.mkdtemp` per entry under `$XDG_RUNTIME_DIR` (or `/tmp`)
2. `rsync -a`-seed it from real `~/<subdir>` if present
3. `--bind` it over `$HOME/<subdir>` inside bwrap
4. `shutil.rmtree` it in the run's `finally` block

`build_bwrap_cmd` filters those subdirs out of `home_ro_dirs` / `home_rw_dirs` so the real dir is never bound — even briefly. Requires `rsync` on the host; agent-sandbox errors out at startup with a clear install hint if it's missing.

Currently only **codex paranoid** (`sandbox/profiles/codex-paranoid.toml`) opts in. Claude still uses the older claude-specific machinery (`[claude] use_real_config = false` → persistent `~/.agent-sandbox/claude-config/`).

## Why this is non-trivial

1. **Behavior change for existing claude users.** Today's normal/permissive levels read/write the real `~/.claude` (when `use_real_config = true`) or the persistent `~/.agent-sandbox/claude-config/` (when `false`). Switching all three levels to ephemeral would mean every claude run starts from scratch — losing learned tool permissions, MCP project configs, recent project list, etc. Acceptable for paranoid, **not** acceptable as the default for normal/permissive.
2. **`~/.claude.json` is a sibling file, not a directory.** It lives at `$HOME/.claude.json` (not inside `~/.claude/`). The current `scratch_home_dirs` mechanism handles directories only — `claude.json` is mounted from `SANDBOX_DIR / "claude.json"` by a separate code branch in `build_bwrap_cmd` (~lines 1798–1815). A full migration needs either a companion `scratch_home_files` field (preferred), or repackaging `~/.claude.json` inside `~/.claude/` (upstream change, not under our control).
3. **`agent-sandbox init` / `merge` / `diff` / `_auto_snapshot`.** These commands assume the persistent `claude-config/` exists and is syncable with real `~/.claude`. They have to be deprecated, gated behind a flag, or rewired (e.g. `init` becomes a no-op for ephemeral; `merge` becomes an explicit copy-back the user invokes from inside the sandbox).
4. **Existing user installs.** Anyone running LINCE today has a populated `~/.agent-sandbox/claude-config/`. The migration must not nuke it; either keep it as the default for normal/permissive, or provide a one-shot `agent-sandbox migrate-claude-config` that rsyncs it back to real `~/.claude`.

## Phase 1 — opt-in for paranoid only (low risk)

- Add `scratch_home_dirs = [".claude"]` to `sandbox/profiles/claude-paranoid.toml`.
- Add a companion `scratch_home_files` mechanism in `agent-sandbox` for `~/.claude.json` (rsync real file into a temp file at spawn, `--bind` over `$HOME/.claude.json`, remove on exit). This is a small, isolated change to `cmd_run` and `build_bwrap_cmd` mirroring the existing `scratch_home_dirs` plumbing.
- Update `claude-paranoid.toml` to use the new mechanism for `.claude.json` too. The result: claude paranoid matches codex paranoid — kernel network isolation **and** ephemeral filesystem on both backends (nono paranoid already does this via the bash wrapper).
- **Do not touch normal/permissive.** `[claude] use_real_config` keeps its current semantics there.
- Update `docs/documentation/dashboard/sandbox-levels.md`: claude paranoid now ephemeral; cross-link to the codex example; `use_real_config` is now a normal/permissive concern only.

## Phase 2 — retire `use_real_config` for normal/permissive (RFC first)

This phase is a behavior change for everyday users. Do **not** start coding without a design doc.

- RFC: how do normal/permissive look without `use_real_config`? Options:
  - Persistent variant of `scratch_home_dirs` (new field, e.g. `persistent_home_dirs = [".claude"]` with destination `~/.agent-sandbox/claude-config/`).
  - Overlayfs copy-on-write — bigger change, portability concerns.
  - Deprecate `claude-config/` and just bind real `~/.claude` rw (matches `use_real_config = true`).
- Refactor or remove `cmd_init` / `cmd_merge` / `cmd_diff` / `_auto_snapshot` accordingly.
- Migration tool (`agent-sandbox migrate-claude-config`) for users with a populated persistent dir.
- Deprecate `[claude] use_real_config` with a warning; eventually remove.
- Remove the claude-specific code path in `build_bwrap_cmd` (lines ~1798–1815).

## Out of scope

- Other agents (gemini/opencode/pi) — they get `scratch_home_dirs` opt-in via LINCE-100/101/102 directly; they never had the `use_real_config` legacy.
- Any change to the nono path (it already uses an equivalent ephemeral wrapper synthesized by the lince-dashboard plugin).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Phase 1: sandbox/profiles/claude-paranoid.toml opts in via [agents.claude] scratch_home_dirs = [".claude"]
- [ ] #2 Phase 1: ~/.claude.json is also ephemeral under paranoid (via new scratch_home_files field or equivalent)
- [ ] #3 Phase 1: 'agent-sandbox run -a claude --sandbox-level paranoid' banner shows the scratch line listing both ~/.claude and ~/.claude.json
- [ ] #4 Phase 1: Inside paranoid, modifications to ~/.claude/ and ~/.claude.json do not persist across runs
- [ ] #5 Phase 1: Normal/permissive behavior unchanged; no regression in init/merge/diff/snapshot-diff
- [ ] #6 Phase 1: docs/documentation/dashboard/sandbox-levels.md updated — claude paranoid filesystem now matches codex paranoid; use_real_config is normal/permissive only
- [ ] #7 Phase 2 (separate sub-task): RFC produced and approved before any code changes
- [ ] #8 Phase 2: agent-sandbox migrate-claude-config tool for existing users
- [ ] #9 Phase 2: [claude] use_real_config removed; build_bwrap_cmd's claude-specific branch removed/refactored
<!-- AC:END -->
