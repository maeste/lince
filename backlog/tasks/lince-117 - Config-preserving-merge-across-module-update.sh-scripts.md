---
id: LINCE-117
title: Config-preserving merge across module update.sh scripts
status: To Do
assignee: []
created_date: '2026-05-11 19:12'
labels:
  - enhancement
  - epic-97
milestone: m-14
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/108'
  - 'https://github.com/RisorseArtificiali/lince/issues/97'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## TLDR

Stop `lince update` from destroying user-customized TOML configs. Introduces a shared `tomlkit`-based merge utility (`lince-cli/lib/config_merge.py`) and rewires each module's `update.sh` to preserve user values while still adding any new keys shipped in the new defaults. Adds a `--reset-config` opt-out on the `lince update` CLI.

## Why

Today's update scripts are destructive:

- `lince-dashboard/update.sh:55-60` — backs up `~/.config/lince-dashboard/config.toml` then overwrites it from defaults. User edits are lost; recovery requires manually diffing `.bak.*` files.
- `sandbox/update.sh:37` — overwrites `~/.agent-sandbox/agents-defaults.toml` with no backup.
- `sandbox/update.sh:46-58` — overwrites `~/.agent-sandbox/profiles/*.toml` likewise.

The first `lince update` shipped via npm would silently wipe out customizations users have accumulated under the old curl-only flow. Must prevent this before #102 (`lince update`) goes live.

Precedent exists: `lince-config` already uses `tomlkit` for surgical format-preserving edits (lines 254-282, import at line 35). `sandbox/update.sh:94-120` already does a narrow regex-based merge for env-passthrough.

## Implementation plan

1. Create `lince-cli/lib/config_merge.py` (tomlkit-based, ~200 lines): `merge_config(user_path, new_default_path, *, dry_run=False) -> MergeResult` where `MergeResult.orphans` lists user keys absent from new defaults. Semantics: user wins for keys in both; new defaults added where missing; orphan user keys preserved AND reported; comments + ordering preserved; always backs up the user file as `<path>.bak.<timestamp>` before writing; fail-safe on malformed input. Also runnable as `python3 -m lince_cli.config_merge <user> <default>`.
2. Unit tests in `lince-cli/tests/test_config_merge.py` covering: empty user file, identical files, user customization preserved, new default key added, orphan key kept+reported, comment preservation, malformed input → no write, dry_run mode.
3. Rewire `lince-dashboard/update.sh`: replace destructive cp at line 60 with the merger; keep the existing timestamped backup (defense in depth); apply same to `agents-defaults.toml` (line 84); stream orphan-warning block to stdout.
4. Rewire `sandbox/update.sh`: leave `config.toml` alone (already non-destructive); switch `agents-defaults.toml` (line 37) and `profiles/*.toml` (lines 46-58) to the merger; the env-passthrough regex at 94-120 is untouched.
5. Add `--reset-config` flag to `lince update` (CLI from #102 / LINCE-111): when set, exports `LINCE_RESET_CONFIG=1` in env for each module's update.sh; modules see that env and skip the merge (back up, then overwrite verbatim). No `--module` scoping in MVP.
6. Document the merge behaviour and the `--reset-config` escape hatch in `lince-cli/README.md` and one-liners in module READMEs.

## Dependencies

- Blocks: #102
- Blocked by: —

## References

- Epic: #97
- Plan: `/home/maeste/.claude/plans/lince-unified-cli-npm.md` (Addendum section)
- Reusable: `lince-config` lines 254-282 (tomlkit style), `sandbox/update.sh:94-120` (narrow merge pattern)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `python3 -m pytest lince-cli/tests/test_config_merge.py` is green across all listed test cases.
- [ ] #2 Dashboard module test: with a custom value in ~/.config/lince-dashboard/config.toml and a new default that adds one key, running lince-dashboard/update.sh preserves the custom value, adds the new key, and produces a .bak.* file.
- [ ] #3 Sandbox module test: adding a user-invented section to agents-defaults.toml survives sandbox/update.sh and is reported in the orphan-warning block.
- [ ] #4 `lince update --reset-config` discards user values, writes defaults verbatim, and creates a .bak.* file. Without the flag, the same install never loses customizations.
- [ ] #5 Malformed user TOML → merger exits non-zero, makes no changes, prints a clear error.
- [ ] #6 Comments and key ordering present in the user file are preserved through a merge.
- [ ] #7 The merger never writes a file that fails `tomlkit.parse()` round-trip.
<!-- AC:END -->
