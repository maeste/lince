---
id: LINCE-104
title: >-
  agents-defaults.toml: split active entries from variants into
  agents-template.toml
status: In Progress
assignee:
  - claude
created_date: '2026-05-05 19:01'
updated_date: '2026-05-05 19:51'
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

Split the variant entries out of `lince-dashboard/agents-defaults.toml` into a new sibling file `agents-template.toml` that is **not** loaded by the dashboard, and add a quickstart multi-select prompt to `install.sh` so users can pick which alternative levels to enable across all supported agents at install time. Apply to both claude and codex — the only agents with variants today.

Tracks GH issue [#59](https://github.com/RisorseArtificiali/lince/issues/59). Land after LINCE-99 merges, before LINCE-100/101/102 start (so gemini/opencode/pi adopt the new layout from day one).

## Why

After LINCE-98 (claude) and LINCE-99 (codex), `agents-defaults.toml` carries long commented blocks (`# [agents.claude-paranoid]`, `# [agents.codex-permissive]`, ...) so users can uncomment to add a variant to the N-picker. The file is hard to skim and gets worse as more agents land — gemini/opencode/pi would each add ~2 commented blocks, ballooning the file by 6 sections of disabled config. Manual uncomment-in-place is also fragile (no syntax highlighting, easy to miss a line, no install-time UX).

The cleaner model is symmetric with how the plugin already handles user overrides: the user's `~/.config/lince-dashboard/config.toml` can carry its own `[agents.<name>]` blocks that the loader merges on top of `agents-defaults.toml`. Today users have to copy-paste from a comment. Making the template a real TOML file in its own right + having the installer offer a multi-select that pulls from it is just better ergonomics for the same mechanism.

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

No commented `[agents.*]` blocks. Header comment points to `agents-template.toml` and explains the override mechanism.

### `lince-dashboard/agents-template.toml` (NOT loaded — reference + install source)

Fully uncommented alternative variants:
- `[agents.claude-paranoid]`
- `[agents.claude-permissive]`
- `[agents.codex-paranoid]`
- `[agents.codex-permissive]`

Header explains:
- The file is **not** read by the dashboard.
- It serves two purposes: copy-paste source for manual edits, **and** the source the install-time multi-select pulls from.
- Per-agent feature support is implicit: if a given agent has a `[agents.<agent>-<level>]` block here, it supports that level. If it doesn't, the level is unsupported for that agent and any installer-level selection is silently skipped for it.

`install.sh` copies the file into `~/.config/lince-dashboard/` alongside `agents-defaults.toml` so users can find it locally without browsing the repo.

LINCE-100/101/102 add their own variants to this same file (paranoid/permissive for gemini, opencode, pi) once they land — never as commented blocks in `agents-defaults.toml`.

## Quickstart UX: multi-select sandbox levels

Add a new step to `lince-dashboard/install.sh` (and any equivalent quickstart flow) that prompts:

```
Which sandbox levels do you want enabled in the N-picker?
[x] normal       (always on — the default level)
[ ] paranoid     (kernel-isolated network, ephemeral home scratch)
[ ] permissive   (gh CLI + GitHub allowlist)
```

- `normal` is always selected, **not** user-changeable; listed for clarity.
- `paranoid` and `permissive` default to **off**; the user opts in.
- Multi-select: any combination is valid.

For each selected level, the installer reads `lince-dashboard/agents-template.toml` and copies every `[agents.<agent>-<level>]` block (and its companion `[agents.<agent>-<level>.env_vars]` block, if present) into the user's `~/.config/lince-dashboard/config.toml`. The plugin's existing user-overlay merge picks them up on the next dashboard launch — they show up as separate `(paranoid)` / `(permissive)` entries in the N-picker.

**Per-agent feature support is implicit in the template file.** If an agent doesn't ship a `[agents.<agent>-<level>]` block in `agents-template.toml`, that level isn't supported for that agent and is silently skipped — the user's selection is honoured for every agent that does support it.

### Idempotency

Re-running `install.sh` must not duplicate blocks. Detect existing `[agents.<agent>-<level>]` headers in the user's `config.toml` and skip already-present blocks. Users who want a fresh state remove the block manually first (consistent with how `install.sh` already handles `config.toml` backups).

### Non-interactive mode

Non-interactive install paths (CI, scripted install, `--yes`) should accept a flag like `--sandbox-levels=paranoid,permissive` (or env var `LINCE_SANDBOX_LEVELS`) to reproduce the multi-select without a TTY prompt. Default for non-interactive: only `normal` (today's behaviour).

## Implementation steps

1. Create `lince-dashboard/agents-template.toml` with the four variants for claude and codex (move them out of `agents-defaults.toml`, uncomment, polish).
2. Strip the commented variant blocks from `lince-dashboard/agents-defaults.toml`. Add a header pointer to `agents-template.toml` and a one-line explanation of how to enable a variant via `config.toml` (or via the install prompt).
3. Update `lince-dashboard/install.sh`:
   - Step 9 (or wherever) copies `agents-template.toml` to `~/.config/lince-dashboard/agents-template.toml`.
   - **New step**: multi-select prompt (paranoid / permissive). For each selected level, parse `agents-template.toml`, find all `[agents.*-<level>]` blocks, and append them (with their `*.env_vars` companions) into `~/.config/lince-dashboard/config.toml`. Skip blocks that are already present.
   - Honour `--sandbox-levels=...` flag (or `LINCE_SANDBOX_LEVELS` env var) for non-interactive runs.
   - Update the printed summary to show which levels were enabled and for which agents.
4. Verify the plugin loader does **not** read `agents-template.toml`. Today the loader reads `agents-defaults.toml` (built-in) and `config.toml` (user overrides). No code change should be needed if we name the new file `agents-template.toml`.
5. Update `docs/documentation/dashboard/sandbox-levels.md` with a new short section: *"How to enable paranoid/permissive variants in the N-picker"*. Cover both the install prompt and the manual copy-from-template flow. Worked example shows the prompt + the resulting `config.toml` snippet.
6. Update the LINCE-setup skill (`lince-dashboard/skills/lince-setup/`) if it references the commented-variant pattern.
7. Re-test: claude (normal) and codex (normal) still spawn from the N-picker as today; running install with paranoid + permissive selected adds both variants for both agents to the picker; re-running install doesn't duplicate.

## Out of scope

- Plugin loader changes (none needed — we just don't add a third source file).
- Changes to how user overrides in `config.toml` are merged (existing mechanism already does what we need).
- Other agents (gemini/opencode/pi). Their tasks (LINCE-100/101/102) are updated to depend on this one and to add their variants directly to `agents-template.toml`. Once they land, the same multi-select prompt automatically picks them up — no install-script change needed per agent.
- A "remove a level" / "uninstall variant" UX. Manual edit of `config.toml` is fine for now.

## Risks

- Users who already uncommented variants in `agents-defaults.toml` lose them on the next `install.sh --update` run. **Mitigation**: install.sh's existing backup behavior (`*.bak.<timestamp>`) preserves the prior file; the migration note in the install summary tells users to re-run install and pick their levels in the new prompt, or to copy from `agents-template.toml` to `config.toml` manually.
- The install prompt parses `agents-template.toml`. Robust TOML parsing in bash is awkward; a simple block-extractor (find `[agents.*-<level>]`, slurp until next top-level `[` or EOF) is enough since the template file is generated by us and follows a known shape. If we want to be safe, do the parse in Python (the install already runs Python via `python3` for some checks) instead of awk/sed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 lince-dashboard/agents-defaults.toml contains no commented [agents.*] blocks; only active entries
- [ ] #2 lince-dashboard/agents-defaults.toml has a header comment pointing to agents-template.toml and explaining the override-via-config.toml mechanism
- [ ] #3 lince-dashboard/agents-template.toml exists with fully uncommented [agents.claude-paranoid], [agents.claude-permissive], [agents.codex-paranoid], [agents.codex-permissive]
- [ ] #4 agents-template.toml has a prominent header making clear it is NOT loaded by the dashboard; it doubles as copy-paste source AND install-time multi-select source
- [ ] #5 lince-dashboard/install.sh copies agents-template.toml into ~/.config/lince-dashboard/ alongside agents-defaults.toml; install summary mentions it
- [ ] #6 install.sh adds a multi-select prompt: normal (locked-on), paranoid, permissive. Selected levels' blocks from agents-template.toml are appended into ~/.config/lince-dashboard/config.toml
- [ ] #7 Per-agent skip semantics: if an agent doesn't have a matching [agents.<agent>-<level>] block in the template, it is silently skipped for that level; selection is honoured for every agent that does support it
- [ ] #8 Idempotent: re-running install.sh does not duplicate [agents.*-<level>] blocks already in the user's config.toml
- [ ] #9 Non-interactive flag (e.g. --sandbox-levels=paranoid,permissive or LINCE_SANDBOX_LEVELS env var) reproduces the multi-select without a TTY prompt; default is 'normal' only
- [ ] #10 Plugin loader is unchanged — it does not read agents-template.toml (verify by inspecting config.rs and any TOML lookup paths)
- [ ] #11 docs/documentation/dashboard/sandbox-levels.md has a 'How to enable paranoid/permissive variants' section covering both the install prompt and the manual copy-from-template flow
- [ ] #12 Re-test: claude (normal) and codex (normal) still spawn from the N-picker; install with paranoid + permissive selected adds both variants for both agents; re-running install doesn't duplicate
- [ ] #13 LINCE-100, LINCE-101, LINCE-102 are updated to depend on this task and to add their variants to agents-template.toml directly (no commented blocks). New agents added there are picked up by the install prompt automatically.
<!-- AC:END -->
