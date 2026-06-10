# Migrating to Config v2 (users)

For people with an existing LINCE install. The *why* is in the
[design doc](design/config-v2-design.md); this page only answers *what do I do*.

## TL;DR

```bash
./quickstart.sh            # or: cd sandbox && ./update.sh ; cd ../lince-dashboard && ./update.sh
lince-config discover      # see what's installed + suggested setup lines
lince-config apply claude+normal+anthropic   # opt into v2 (one line per agent)
lince-config validate --target lince         # verify
```

No `lince.toml`? **Nothing breaks.** Your old config files keep working
through the dual-read window (see timeline below).

## What happens automatically

| Thing | Behavior |
|---|---|
| Old config files (`~/.agent-sandbox/config.toml`, `~/.config/lince-dashboard/config.toml`) | Still read, as long as `~/.config/lince/lince.toml` does **not** exist (dual-read) |
| Shipped agent definitions | Now installed once to `~/.local/share/lince/registry.d/` (always overwritten on update — never edit them) |
| Legacy `agents-defaults.toml` copies | Kept installed during the window; the `~/.local/bin/agents-defaults.toml` duplicate is removed |
| Dashboard | Reads everything via `lince-config resolve --json` — same results on both paths |

## The one hard switch

Creating `~/.config/lince/lince.toml` (the first `lince-config apply` or
`lince-config set --target lince`) makes it the **only** source: the old
config files stop being read for agents/providers. If they still contain
real customizations, `apply` **refuses** and lists them — migrate those keys
first (table below), or pass `--force-v2` to proceed anyway.

## What you must migrate manually

| Legacy (where) | New location (how) |
|---|---|
| `[providers.vertex]` / `[claude.profiles.zai]` etc. in sandbox config | `[providers.<name>]` in `lince.toml` (env-var **names** + hosts; values stay in your shell env) |
| `default_profile` / `default_provider` in `[sandbox]` | `lince-config apply <agent>+<provider>` (per-agent), or `[sandbox] default_provider` in `lince.toml` |
| `sandbox_level = "paranoid"` on `[agents.<x>]` (dashboard config) | `lince-config apply <agent>+paranoid` |
| Custom agents in `agents-defaults.toml` or `config.toml [agents.*]` | `[agents.<name>]` in `lince.toml` — 4 required keys (`binary`, `display_name`, `short_label`, `color`), the rest is derived. Worked example: design doc §7.2 |
| `[security] allow_domains` | `[network] allowed_hosts` in `lince.toml` |
| Raw mechanism tweaks (extra bwrap args, …) | `[experimental]` in `lince.toml` — voids the default-deny guarantee **visibly** |
| `[logging]` / `[snapshot]` / `[git]` | Same tables, copied 1:1 |

An automatic `lince config migrate` ships with the unified `lince` CLI
(m-14); until then the table above is the migration.

## How to verify

```bash
lince-config validate --target lince     # ✓ … is valid.  (zero warnings)
lince-config resolve --agent claude      # JSON: check "level", "provider",
                                         # "guarantee": "default-deny"
```

Healthy output: your chosen level/provider under `"origin": {"level": "user"}`,
`"guarantee": "default-deny"`, and a `warnings: []` array.

## Rollback

- v2 is opt-in and reversible: **delete (or rename) `~/.config/lince/lince.toml`**
  and resolution returns to your legacy files — they were never modified.
- `update.sh` config merges back up to `*.bak.<timestamp>` next to each file.
- Pin a previous version: check out the previous git tag and re-run the
  module `install.sh` scripts.

## Deprecation timeline

| Release | Behavior |
|---|---|
| 2.0 (now) | `lince.toml` + `registry.d/` introduced; dual-read active; everything keeps working without action |
| 2.1 | Dual-read still active; a migration notice prints on every run |
| 2.2 | Legacy-only installs hard-error: `legacy config found but schema 2.2 requires lince.toml. Run: lince config migrate` |
