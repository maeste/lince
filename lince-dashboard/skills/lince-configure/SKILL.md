---
name: lince-configure
description: Configure LINCE sandbox and dashboard settings in natural language. Use when asked to set up providers, change security levels, modify agent settings, configure API keys, adjust sandbox behavior, or any "how do I configure" question about LINCE. Drives the Config v2 policy layer (~/.config/lince/lince.toml) through the lince-config CLI — apply/set/validate only, never direct TOML edits.
license: MIT
compatibility: Requires lince-config CLI installed (lince-config/install.sh). Python 3.11+ with tomlkit.
metadata:
  author: lince
  version: "2.0"
allowed-tools: Bash(lince-config:*) Read(//home/**/.config/lince/**) Read(//home/**/.agent-sandbox/**) Read(//home/**/.config/lince-dashboard/**)
---

# lince-configure: Natural Language Configuration for LINCE (Config v2)

Translate user intent into **policy** — `lince-config apply` / `lince-config set
--target lince` on `~/.config/lince/lince.toml` — never direct TOML edits, never
mechanism-level keys (bwrap args, profiles fragments, registry files). Validate
after every change and report the diff.

## Hard Rules

1. **CLI only**: every change goes through `lince-config`. NEVER edit a TOML
   file directly. NEVER write into `registry.d/` or any `agents-defaults.toml`
   (shipped data, overwritten on update).
2. **Schema only**: write only keys that exist in the policy schema
   ([references/lince-policy.md](references/lince-policy.md)). If an intent has
   no schema key, say so and propose the closest supported policy (or
   `[experimental]`, with its guarantee-voiding warning) — do not invent keys.
3. **Propose from the catalog**: compositions come from `lince-config
   templates --json` and `lince-config discover --json` — never from memory.
4. **Validate + diff after every write**: `lince-config validate --target
   lince` must pass; show the user what changed (`apply` prints it; for `set`,
   read back the key).
5. **Secrets stay out of policy**: v2 providers carry env-var **names** —
   API keys live in the user's shell environment, not in `lince.toml`.
   Never display a full key; mask to the first 8 chars.

## CLI Surface

```bash
lince-config discover [--json]                 # installed agents + suggested apply lines
lince-config templates [--json]                # the composition catalog (agents/levels/providers)
lince-config apply <agent>[+<level>][+<provider>] [--dry-run] [--project DIR]
lince-config get|set|append|remove|unset <key> [<value>] --target lince [-q]
lince-config validate --target lince [--json]
lince-config resolve [--agent NAME]            # the resolved view (origin of every value)
```

Legacy v1 targets (`--target sandbox|dashboard`) still work for installs that
have not switched to v2 — see "Legacy installs" below.

## Workflow

### Step 0: Interaction style (only for vague openings)

If the user's first message has no specific request ("help me configure
LINCE"), offer via `AskUserQuestion`: **Conversational** vs **Guided menu**
(then use `AskUserQuestion` at every decision point). Match the user's
language. If intent is already clear, skip this.

### Step 1: Read the state

```bash
lince-config discover --json     # what's installed, which credentials detected
lince-config resolve --json      # current effective config (or its error)
```

`resolve` tells you whether the install is v2 (`sources.user` set) or still
dual-read (`sources.legacy`).

### Step 2: Translate intent → policy

| User says | Policy action |
|---|---|
| "make codex paranoid but allow github.com" | `lince-config apply codex+paranoid` then `lince-config append agents.codex.allowed_hosts github.com --target lince -q` |
| "add my OpenRouter key" | Key goes in the **host env**: have them add `export OPENROUTER_API_KEY=...` to their shell profile; then `lince-config apply <agent>+openrouter` — `templates` shows it as available once the env var is set |
| "use Vertex for Claude" | `lince-config set providers.vertex.env '["CLAUDE_CODE_USE_VERTEX", "ANTHROPIC_VERTEX_PROJECT_ID", "CLOUD_ML_REGION"]' --target lince -q` then `lince-config apply claude+vertex` (values exported in host env) |
| "more security" / "paranoid mode" | `lince-config apply <agent>+paranoid` (per agent — explain with [references/sandbox-levels.md](references/sandbox-levels.md)) |
| "allow pypi everywhere" | `lince-config append network.allowed_hosts pypi.org --target lince -q` |
| "only show claude and codex in the dashboard" | `lince-config set dashboard.enabled_agents '["claude", "codex"]' --target lince -q` |
| "add a custom agent" | Use the `/lince-add-supported-agent` skill (registry-shaped `[agents.<name>]` entry) |
| "show my config" | `lince-config resolve --json` → summarize per agent (level, provider, origin) |
| "something's broken" | `lince-config validate --target lince` + `lince-config check` → diagnose |

### Step 3: Apply (smallest change first)

Prefer `apply` (composes + validates + idempotent) over raw `set`. Use
`--dry-run` to show the diff before a change the user might question.

### Step 4: Verify and explain

```bash
lince-config validate --target lince
lince-config resolve --agent <changed-agent>
```

Report: what changed (file + keys), what it means in plain language, and any
warnings. If validation fails, revert the key you set (`unset`) and explain.

## The v2 switch (first write on a legacy install)

The first `apply`/`set --target lince` creates `lince.toml`, which becomes the
ONLY config source — legacy files stop being read. `apply` refuses when the
legacy files still hold real customizations and lists them:

1. Show the user the listed items and the mapping table in
   `docs/migration-v2-users.md`.
2. Recreate each item in `lince.toml` (providers → `[providers.<name>]` with
   env **names**; agent overrides → `[agents.<name>]`; `allow_domains` →
   `network.allowed_hosts`).
3. Re-run the original command. Use `--force-v2` only if the user explicitly
   confirms they want the legacy customizations ignored.

## Legacy installs (user declines v2)

If the user explicitly does not want `lince.toml` yet, fall back to the v1
targets (`--target sandbox|dashboard`) with the key tables in
[references/sandbox-config.md](references/sandbox-config.md) /
[references/dashboard-config.md](references/dashboard-config.md). Mention the
migration guide once; do not push.

## References (loaded on demand)

| Topic | File |
|---|---|
| v2 policy keys (generated from schema) | [references/lince-policy.md](references/lince-policy.md) |
| Sandbox levels explained | [references/sandbox-levels.md](references/sandbox-levels.md) |
| Provider concepts | [references/providers.md](references/providers.md) |
| Security model | [references/security.md](references/security.md) |
| Legacy v1 sandbox keys (generated) | [references/sandbox-config.md](references/sandbox-config.md) |
| Legacy v1 dashboard keys (generated) | [references/dashboard-config.md](references/dashboard-config.md) |

## Security Notes

- Mask API keys (first 8 chars + "…") whenever one appears in output.
- v2: keys belong in the host environment; `lince.toml` carries names only.
  If the user pastes a key, tell them where to export it — do not write it
  into any config file.
- Legacy v1 configs may hold literal keys: the file must be `chmod 600`
  (`lince-config check` warns).
- `[experimental]` keys void the default-deny guarantee **visibly**
  (`resolve` reports `"guarantee": "void:<key>"`) — always warn before
  setting one.
- paranoid pairs kernel isolation with the credential proxy; if an apply at
  paranoid fails at launch time, point at the effective-policy record
  (`/tmp/lince-dashboard/<id>.policy.json`) which names the missing boundary.
