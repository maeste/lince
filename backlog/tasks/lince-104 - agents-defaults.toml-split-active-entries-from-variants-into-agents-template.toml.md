---
id: LINCE-104
title: >-
  agents-defaults.toml: split active entries from variants into
  agents-template.toml
status: To Do
assignee: []
created_date: '2026-05-05 19:01'
labels:
  - lince-dashboard
  - refactor
  - follow-up
milestone: m-13
dependencies:
  - LINCE-99
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/59'
  - lince-dashboard/agents-defaults.toml
  - lince-dashboard/install.sh
  - docs/documentation/dashboard/sandbox-levels.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Scope

Split the variant entries out of `lince-dashboard/agents-defaults.toml` into a new sibling file `agents-template.toml` that is **not** loaded by the dashboard. The defaults file then contains only active entries (one per agent + `-unsandboxed` variants). Apply to both claude and codex — the only agents with variants today.

Tracks GH issue [#59](https://github.com/RisorseArtificiali/lince/issues/59). Land after LINCE-99 merges, before LINCE-100/101/102 start (so gemini/opencode/pi adopt the new layout from day one).

## Why

After LINCE-98 (claude) and LINCE-99 (codex), `agents-defaults.toml` carries long commented blocks (`# [agents.claude-paranoid]`, `# [agents.codex-permissive]`, ...) so users can uncomment to add a variant to the N-picker. The file is hard to skim and gets worse as more agents land — gemini/opencode/pi would each add ~2 commented blocks, ballooning the file by 6 sections of disabled config.

The cleaner model is symmetric with how the plugin already handles user overrides: the user's `~/.config/lince-dashboard/config.toml` can carry its own `[agents.<name>]` blocks that the loader merges on top of `agents-defaults.toml`. Today users have to either uncomment-in-place inside `agents-defaults.toml` or copy-paste from a comment. Making the template a real TOML file in its own right is just better ergonomics for the same mechanism.

## File layout after this task

### `lince-dashboard/agents-defaults.toml` (loaded)

Only active entries:
- `[agents.claude]` (normal)
- `[agents.claude-unsandboxed]`
- `[agents.codex]` (normal)
- `[agents.codex-unsandboxed]`
- `[agents.gemini]`, `[agents.gemini-bwrap]`, `[agents.gemini-nono]` (until LINCE-100 collapses them)
- `[agents.opencode]`, `[agents.opencode-bwrap]`, `[agents.opencode-nono]` (until LINCE-101)
- `[agents.pi]`, `[agents.pi-bwrap]`, `[agents.pi-nono]` (until LINCE-102)

No commented `[agents.*]` blocks. A header comment at the top points to `agents-template.toml` and explains the override mechanism.

### `lince-dashboard/agents-template.toml` (NOT loaded — reference only)

Fully uncommented alternative variants:
- `[agents.claude-paranoid]`
- `[agents.claude-permissive]`
- `[agents.codex-paranoid]`
- `[agents.codex-permissive]`

Header explains:
- This file is **not** read by the dashboard.
- It is a copy-paste source for users who want to add a variant to their N-picker.
- The user copies the desired block into their own `~/.config/lince-dashboard/config.toml`. The plugin's loader then merges it on top of `agents-defaults.toml` and the variant appears in the N-picker.

`install.sh` copies the file into `~/.config/lince-dashboard/` alongside `agents-defaults.toml` so users can find it locally without browsing the repo.

LINCE-100/101/102 add their own variants to this same file (paranoid/permissive for gemini, opencode, pi) once they land — never as commented blocks in `agents-defaults.toml`.

## Implementation steps

1. Create `lince-dashboard/agents-template.toml` with the four variants for claude and codex (move them out of `agents-defaults.toml`, uncomment, polish).
2. Strip the commented variant blocks from `lince-dashboard/agents-defaults.toml`. Add a header pointer to `agents-template.toml` and a one-line explanation of how to enable a variant via `config.toml`.
3. Update `lince-dashboard/install.sh`:
   - Step 9 (or wherever) copies `agents-template.toml` to `~/.config/lince-dashboard/agents-template.toml`.
   - Update the printed summary to mention the new file.
4. Verify the plugin loader does **not** read `agents-template.toml`. Today the loader reads `agents-defaults.toml` (built-in) and `config.toml` (user overrides). No code change should be needed if we name the new file `agents-template.toml` (i.e. not matching either expected filename).
5. Update `docs/documentation/dashboard/sandbox-levels.md` with a new short section: *\"How to enable a paranoid/permissive variant in the N-picker\"*. Worked example: copy `[agents.claude-paranoid]` from `~/.config/lince-dashboard/agents-template.toml` into `~/.config/lince-dashboard/config.toml`, restart the dashboard, the entry shows up.
6. Update the LINCE-setup skill (`lince-dashboard/skills/lince-setup/`) if it references the commented-variant pattern.
7. Re-test: claude (normal) and codex (normal) still spawn from the N-picker as today; copying a variant block from the template file into a fresh `config.toml` and restarting the dashboard adds the variant to the picker.

## Out of scope

- Plugin loader changes (none needed — we just don't add a third source file).
- Changes to how user overrides in `config.toml` are merged (existing mechanism already does what we need).
- Other agents (gemini/opencode/pi). Their tasks (LINCE-100/101/102) are updated to depend on this one and to add their variants directly to `agents-template.toml`.

## Risks

- Users who already uncommented variants in `agents-defaults.toml` lose them on the next `install.sh --update` run. **Mitigation**: install.sh's existing backup behavior (`*.bak.<timestamp>`) preserves the prior file; the migration note in the install summary tells users to re-add their variants by copying from `agents-template.toml` into their `config.toml`.
- Copy-paste workflow vs. uncomment-in-place is one extra step. Acceptable trade for a cleaner defaults file and proper TOML for the templates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 lince-dashboard/agents-defaults.toml contains no commented [agents.*] blocks; only active entries
- [ ] #2 lince-dashboard/agents-defaults.toml has a header comment pointing to agents-template.toml and explaining the override-via-config.toml mechanism
- [ ] #3 lince-dashboard/agents-template.toml exists with fully uncommented [agents.claude-paranoid], [agents.claude-permissive], [agents.codex-paranoid], [agents.codex-permissive]
- [ ] #4 agents-template.toml has a prominent header making clear it is NOT loaded by the dashboard and is a copy-paste source
- [ ] #5 lince-dashboard/install.sh copies agents-template.toml into ~/.config/lince-dashboard/ alongside agents-defaults.toml; install summary mentions it
- [ ] #6 Plugin loader is unchanged — it does not read agents-template.toml (verify by inspecting config.rs and any TOML lookup paths)
- [ ] #7 docs/documentation/dashboard/sandbox-levels.md has a 'How to enable a paranoid/permissive variant' section with a worked copy-from-template example
- [ ] #8 Re-test: claude (normal) and codex (normal) still spawn from the N-picker; copying [agents.claude-paranoid] from the template into a user's config.toml adds it to the picker after dashboard restart
- [ ] #9 LINCE-100, LINCE-101, LINCE-102 are updated to depend on this task and to add their variants to agents-template.toml directly (no commented blocks)
<!-- AC:END -->
