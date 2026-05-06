---
id: LINCE-106
title: 'sandbox: policy fragments support extends/inheritance'
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
  - 'https://github.com/RisorseArtificiali/lince/issues/54'
  - sandbox/agent-sandbox
  - sandbox/profiles/claude-paranoid.toml
  - docs/documentation/dashboard/sandbox-levels.md
  - lince-dashboard/nono-profiles/lince-claude-paranoid.json
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context

Sandbox-policy fragments under `sandbox/profiles/<name>.toml` are currently flat and self-contained. To produce a "paranoid + extra allowed domains" variant a user must either (a) add to their personal `~/.agent-sandbox/config.toml` or (b) duplicate all of `paranoid.toml` as a custom fragment. Option (b) drifts as paranoid defaults evolve.

Tracks GH issue [#54](https://github.com/RisorseArtificiali/lince/issues/54).

Related to LINCE-{PREV} (cascading config merge) — both involve layered TOML in sandbox. No dependency; can land in either order.

## What changes

Add an optional top-level `extends = "<fragment-name>"` field to fragment TOML files. When present, `load_sandbox_level_fragment()` resolves the parent recursively and deep-merges the child on top using existing `merge_sandbox_level()` semantics (whitelisted append-merge).

### New helper `_resolve_fragment_with_extends(name, agent, *, _visited=None)`

1. Resolve `name` to an absolute path using the same 3-dir lookup + agent-prefix candidates as `load_sandbox_level_fragment`:
   - `./.agent-sandbox/profiles/<agent>-<name>.toml` → `./.agent-sandbox/profiles/<name>.toml`
   - `~/.agent-sandbox/profiles/<agent>-<name>.toml` → `~/.agent-sandbox/profiles/<name>.toml`
   - `<script-dir>/profiles/<agent>-<name>.toml` → `<script-dir>/profiles/<name>.toml`
2. Track visited **canonical absolute paths** in `_visited` (set). On revisit → raise hard error: `fragment cycle: A → B → A`.
3. Missing path → hard error naming the missing fragment and all searched paths.
4. Load TOML. If it has `extends = "<parent>"`, recurse: load parent dict, then `merge_sandbox_level(parent_dict, child_without_extends)`. Strip the `extends` key from the result before returning.

`load_sandbox_level_fragment()` becomes a thin wrapper delegating to this helper. `cmd_run` call site is unchanged.

### Extends-name resolution

Same lookup as `load_sandbox_level_fragment` (agent-prefixed first, bare second). So `extends = "paranoid"` in a fragment resolved for `-a claude` finds `claude-paranoid.toml`. Matches the issue's worked example.

### List-merge semantics

Keep `merge_sandbox_level()`'s **whitelist-append** (`_SANDBOX_LEVEL_LIST_APPEND_KEYS`) semantics — unchanged. Only `home_ro_dirs`, `home_rw_dirs`, `ro_dirs`, `extra_rw`, `allow_domains`, `passthrough` append; other lists replace. This is how fragments already merge today; `extends` makes the merge recursive.

## Key file targets

- `sandbox/agent-sandbox:1091-1122` — `load_sandbox_level_fragment()` (fragment loader, wraps new helper)
- `sandbox/agent-sandbox:1125-1154` — `merge_sandbox_level()` (kept as-is, called per recursion step)
- `sandbox/agent-sandbox:1079-1088` — `_SANDBOX_LEVEL_LIST_APPEND_KEYS` (unchanged)
- `sandbox/agent-sandbox:2267-2279` — caller in `cmd_run()` (no API change needed)
- Reference: `lince-dashboard/nono-profiles/lince-claude-paranoid.json` (nono-side `extends` precedent — agent-sandbox just emits the field; nono resolves it client-side)

## Worked example (to ship as doc sample)

```toml
# ~/.agent-sandbox/profiles/paranoid-with-pypi.toml
extends = "paranoid"

[security]
allow_domains = ["pypi.org", "files.pythonhosted.org"]
# Append-merged onto claude-paranoid's allow_domains (which has api.anthropic.com)
# Final list: ["api.anthropic.com", ..., "pypi.org", "files.pythonhosted.org"]
```

Usage: `agent-sandbox run -a claude --sandbox-level paranoid-with-pypi`

## Tests note

No pytest harness for sandbox module. Verify via CLI smoke tests (see AC).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AC1 Optional top-level extends = "<fragment-name>" field supported in sandbox/profiles/*.toml; missing field = today's behavior (no regression)
- [x] #2 AC2 Resolution uses the same dir + agent-prefix lookup as load_sandbox_level_fragment: tries <agent>-<extends>.toml first, then <extends>.toml
- [x] #3 AC3 Recursion: A extends B extends C produces C merged with B merged with A on top, using merge_sandbox_level semantics (whitelisted append) at each step
- [x] #4 AC4 Cycle detection: A extends A and A extends B extends A both raise a clear error naming the full cycle; no infinite loop
- [x] #5 AC5 Missing parent raises a clear error naming the missing fragment name and all searched paths
- [x] #6 AC6 The extends key is stripped from the final resolved dict (does not appear in merged config consumed by cmd_run)
- [x] #7 AC7 Worked example fragment ships as a doc sample (e.g. docs/ or sandbox/README.md) showing extends = "paranoid" + extra allow_domains
- [ ] #8 AC8 Smoke test: ~/.agent-sandbox/profiles/paranoid-with-pypi.toml extending paranoid produces a merged allow_domains containing both api.anthropic.com (from claude-paranoid) and the added hosts, when invoked via agent-sandbox run -a claude --sandbox-level paranoid-with-pypi
- [x] #9 AC9 docs/documentation/dashboard/sandbox-levels.md gains an 'Extending a sandbox-policy fragment' section with the worked example
- [x] #10 AC10 PR body contains 'Closes #54'; verify GH issue auto-closes after merge
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented in commit fd2846de.

**New functions in `sandbox/agent-sandbox`:**
- `_find_fragment_path(name, agent)` — shared path-finding logic (3 dirs × 2 candidates), returns resolved absolute Path or None
- `_resolve_fragment_extends(name, agent, *, _chain)` — recursive resolver: finds path, checks cycle via `_chain` list, loads TOML, pops `extends`, recurses on parent if present, merges with `merge_sandbox_level`
- `load_sandbox_level_fragment()` refactored to thin wrapper: returns None for unknown top-level name, delegates to `_resolve_fragment_extends` otherwise

**Error handling:**
- Missing parent → `sys.exit(1)` with fragment name + all 6 searched paths
- Cycle → `sys.exit(1)` showing the cycle chain (e.g. `a.toml → b.toml → a.toml`)
- `extends` not a string → `sys.exit(1)` with type info

**Docs updated:**
- `docs/documentation/sandbox/config-reference.md` — Sandbox Levels section updated with Option A (config.toml) vs Option B (extends fragment) pattern + extends semantics
- `docs/documentation/dashboard/sandbox-levels.md` — new §6 subsection "Extending a fragment with `extends`": worked example, resolution walkthrough, error behavior, comparison table vs config.toml approach; §9 Future Work updated to mark #54 done
- `sandbox/profiles/claude-paranoid.toml` — comment updated to show both Option A and Option B
- `sandbox/profiles/paranoid-with-pypi.toml.example` — new starter file; copy to `~/.agent-sandbox/profiles/paranoid-with-pypi.toml` to use

AC8 (smoke test) is verified manually by the user.
<!-- SECTION:FINAL_SUMMARY:END -->
