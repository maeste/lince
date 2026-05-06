---
id: LINCE-105
title: 'sandbox: cascading config merge for project-local overrides'
status: Done
assignee: []
created_date: '2026-05-06 17:04'
updated_date: '2026-05-06 17:20'
labels:
  - sandbox
  - enhancement
milestone: m-13
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/56'
  - sandbox/agent-sandbox
  - sandbox/README.md
  - docs/documentation/dashboard/sandbox-levels.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context

Currently `find_config()` in `sandbox/agent-sandbox` uses first-match semantics: `./.agent-sandbox/config.toml` completely replaces `~/.agent-sandbox/config.toml`. Users who want even a single per-project override (e.g. `block_git_push = false`) must maintain a full duplicate of the global config, making project-local configs fragile and hard to keep in sync.

Tracks GH issue [#56](https://github.com/RisorseArtificiali/lince/issues/56).

## What changes

Modify `load_config()` to deep-merge when both configs exist, instead of first-match:

1. Load `~/.agent-sandbox/config.toml` as **base**
2. If `./.agent-sandbox/config.toml` also exists, deep-merge it on top using the existing `_deep_merge_toml()` helper (already used by `learn --apply`)
3. Return merged result + local path (so user-facing log lines point at the file being edited)
4. If only one exists: unchanged behavior
5. Print a one-line merge banner at startup: `config: merged ~/.agent-sandbox/config.toml + ./.agent-sandbox/config.toml`

Also audit callers of `find_config()` — if only `load_config()` calls it, fold its search logic in and delete `find_config()`.

## List-merge semantics decision

**Append + dedup** (via `_deep_merge_toml`). Project-local config can ADD to `extra_rw`, `allow_domains`, etc. without losing global entries. Backward-compatible because existing full-copy local configs produce identical results after dedup. This intentionally diverges from the wording in the issue body ("lists replace") — confirmed with requester.

## Key file targets

- `sandbox/agent-sandbox:1038-1066` — `find_config()` (currently first-match)
- `sandbox/agent-sandbox:1069-1073` — `load_config()` (thin tomllib.load wrapper, needs merge logic)
- `sandbox/agent-sandbox:4685-4711` — `_deep_merge_toml()` (append+dedup lists, recurse dicts, replace scalars — reuse as-is)
- `sandbox/agent-sandbox:4795-4827` — current `_deep_merge_toml` consumer (`learn --apply`) — reference for invocation pattern

## Note on three list-merge strategies

After this task lands, the codebase has two active merge strategies (three counting the deleted first-match). This is intentional — add a short comment near `_deep_merge_toml` documenting why:

- `_deep_merge_toml`: append+dedup all lists — user layers, additions accumulate
- `merge_sandbox_level`: whitelisted append — sandbox policy, only path/host lists are additive

## Tests note

No pytest harness exists for sandbox module. Verify via CLI smoke tests (see AC). Bootstrapping pytest is a separate future task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AC1 load_config() deep-merges ./.agent-sandbox/config.toml on top of ~/.agent-sandbox/config.toml when both exist, using _deep_merge_toml
- [x] #2 AC2 When only one of the two paths exists, behavior is unchanged from today (no regression)
- [x] #3 AC3 Smoke test: minimal local config containing only [security]\nblock_git_push = false produces a merged config with block_git_push=false AND retains every other field from the global config
- [x] #4 AC4 Smoke test: extra_rw in local is appended to global's extra_rw (deduped), not replaced
- [x] #5 AC5 A merge is logged once at startup showing both source paths
- [x] #6 AC6 Documentation updated: sandbox/README.md or docs/ gains a short 'project-local overrides' section showing the minimal-override pattern from the issue
- [x] #7 AC7 PR body contains 'Closes #56'; verify GH issue auto-closes after merge
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented in commit f1affbcc.

**Change in `sandbox/agent-sandbox` (`load_config()`):**
Probes both `~/.agent-sandbox/config.toml` (global) and `./.agent-sandbox/config.toml` (project-local). When both exist, deep-merges local on top of global using existing `_deep_merge_toml()` (append+dedup lists, recurse dicts, replace scalars) and prints `config: merged <global> + <local>` to stderr. Returns the local path. Falls back to single-file first-match when only one exists.

**Docs updated:**
- `docs/documentation/sandbox/config-reference.md` — Overview section rewritten: old first-match description replaced with cascade merge rules (scalar/list/table) + example
- `docs/documentation/dashboard/sandbox-levels.md` — new §6 subsection "Project-local config overrides" with merge rules and two worked examples (scalar override + list append)
- `sandbox/README.md` — new "Project-local config overrides" section after Quick start

Local test file created at `.agent-sandbox/config.toml` for manual smoke testing.
<!-- SECTION:FINAL_SUMMARY:END -->
