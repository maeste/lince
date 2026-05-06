---
id: LINCE-103
title: >-
  claude paranoid: opt into scratch_home_dirs / scratch_home_files (Phase 1
  only)
status: To Do
assignee: []
created_date: '2026-05-05 18:13'
updated_date: '2026-05-06 14:10'
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

Migrate **claude paranoid** off the bespoke `[claude] use_real_config` mechanism onto the generic `scratch_home_dirs` mechanism introduced in LINCE-99. Add a companion `scratch_home_files` for the sibling `~/.claude.json`.

This task is **Phase 1 only**. The original Phase 2 (broader retirement of `use_real_config` for normal/permissive) is **dropped** — see "Out of scope" below.

Tracks GH issue [#58](https://github.com/RisorseArtificiali/lince/issues/58).

## Background — what LINCE-99 shipped

LINCE-99 introduced a **generic ephemeral scratch mechanism** in `sandbox/agent-sandbox`: an agent-config field `scratch_home_dirs = [".codex"]` that makes `cmd_run` (bwrap path):

1. `tempfile.mkdtemp` per entry under `$XDG_RUNTIME_DIR` (or `/tmp`)
2. `rsync -a`-seed it from real `~/<subdir>` if present
3. `--bind` it over `$HOME/<subdir>` inside bwrap
4. `shutil.rmtree` it in the run's `finally` block

`build_bwrap_cmd` filters those subdirs out of `home_ro_dirs` / `home_rw_dirs` so the real dir is never bound — even briefly. Requires `rsync` on the host; agent-sandbox errors out at startup with a clear install hint if it's missing.

Currently only **codex paranoid** opts in. Claude paranoid still uses the older claude-specific machinery.

## What changes (Phase 1)

- Add `scratch_home_dirs = [".claude"]` to `sandbox/profiles/claude-paranoid.toml`.
- Add a new `scratch_home_files` mechanism in `agent-sandbox` for sibling files (rsync real file into a temp file at spawn, `--bind` over `$HOME/.claude.json`, remove on exit). Mirrors the existing `scratch_home_dirs` plumbing.
- Update `claude-paranoid.toml` to use `scratch_home_files = [".claude.json"]` too. End state: claude paranoid matches codex paranoid — kernel network isolation **and** ephemeral filesystem on both backends.
- Make claude paranoid bypass the `use_real_config` claude-config code path (since it now uses the generic scratch mechanism instead).
- **Do not touch normal/permissive.** `[claude] use_real_config` keeps its current semantics for those levels.
- Update `docs/documentation/dashboard/sandbox-levels.md`: claude paranoid now ephemeral; document `use_real_config` as a **claude-only, normal/permissive-only** knob.

## Scope of `use_real_config` after this task

`[claude] use_real_config` is **explicitly scoped to**:
- The **claude** agent only (no other agent has or will get this knob).
- **Normal** and **permissive** sandbox levels only. Paranoid ignores it (paranoid is always ephemeral via `scratch_home_dirs` / `scratch_home_files`).

This must be documented in `sandbox-levels.md` and reflected in the implementation (paranoid takes the scratch path, not the use_real_config branch).

## Out of scope — Phase 2 dropped

The original Phase 2 ("retire `use_real_config` for normal/permissive") is **explicitly dropped**:

- No RFC, no overlayfs experiment, no `persistent_home_dirs` field.
- No migration tool (`agent-sandbox migrate-claude-config`).
- No removal of `cmd_init` / `cmd_merge` / `cmd_diff` / `_auto_snapshot`.
- No removal of the claude-specific branch in `build_bwrap_cmd`.

The persistent `~/.agent-sandbox/claude-config/` workflow stays as the default for normal/permissive indefinitely. If we ever revisit, it will be a separate task with its own RFC.

Also out of scope:
- Other agents (gemini/opencode/pi) — they get `scratch_home_dirs` opt-in via LINCE-100/101/102 directly; they never had the `use_real_config` legacy.
- Any change to the nono path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 sandbox/profiles/claude-paranoid.toml opts in via scratch_home_dirs = [".claude"] and scratch_home_files = [".claude.json"]
- [ ] #2 agent-sandbox supports a new scratch_home_files agent-config field, mirroring scratch_home_dirs
- [ ] #3 ~/.claude.json is ephemeral under paranoid (rsync-seeded temp file, bind-mounted, removed on exit)
- [ ] #4 agent-sandbox run -a claude --sandbox-level paranoid banner shows the scratch line listing both ~/.claude and ~/.claude.json
- [ ] #5 Inside paranoid, modifications to ~/.claude/ and ~/.claude.json do not persist across runs
- [ ] #6 Normal/permissive behavior unchanged; no regression in init/merge/diff/snapshot-diff
- [ ] #7 docs/documentation/dashboard/sandbox-levels.md updated: claude paranoid filesystem matches codex paranoid; use_real_config documented as claude-only, normal/permissive-only
- [ ] #8 Phase 2 explicitly dropped — no removal of use_real_config or claude-specific commands
<!-- AC:END -->
