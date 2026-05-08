---
name: lince-configure
description: Configure LINCE sandbox and dashboard settings in natural language. Use when asked to set up providers, change security levels, modify agent settings, configure API keys, adjust sandbox behavior, or any "how do I configure" question about LINCE. Handles both sandbox (~/.agent-sandbox/config.toml) and dashboard (~/.config/lince-dashboard/config.toml) configuration.
license: MIT
compatibility: Requires lince-config CLI installed (lince-config/install.sh). Python 3.11+ with tomlkit.
metadata:
  author: lince
  version: "1.0"
allowed-tools: Bash(lince-config:*) Read(//home/**/.agent-sandbox/**) Read(//home/**/.config/lince-dashboard/**)
---

# lince-configure: Natural Language Configuration for LINCE

Configure LINCE (sandbox + dashboard) through conversation. This skill reads the
documentation, understands the user's intent, and uses `lince-config` CLI to make
changes safely — never editing TOML files directly.

## Available Tools

| Tool | Path | Description |
|------|------|-------------|
| CLI | `lince-config` | Structured read/write for TOML config (preserves comments/formatting) |
| Docs | `references/` | Configuration reference docs loaded on-demand |

## CLI Reference (lince-config)

All commands accept `--target sandbox` (default) or `--target dashboard`.

```bash
# Read
lince-config get <dotted.key> [--json]                  # e.g. security.unshare_net
lince-config list [section] [--json]                    # e.g. providers, agents

# Write
lince-config set <dotted.key> <value> [-q]              # auto-coerces bool/int/str
lince-config append <dotted.key> <value> [-q]           # append to list (dedup)
lince-config remove <dotted.key> <value> [-q]           # remove from list
lince-config unset <dotted.key> [-q]                    # remove key/section

# Diagnostics
lince-config check [--json]                             # doctor-style checks
lince-config validate [--json]                          # schema validation
```

Always use `-q` (quiet) for write operations during guided setup to keep output clean.
Always use `--json` for read operations to parse results programmatically.

## Configuration Targets

| Target | File | Purpose |
|--------|------|---------|
| `sandbox` | `~/.agent-sandbox/config.toml` | Sandbox behavior, providers, agents, security |
| `dashboard` | `~/.config/lince-dashboard/config.toml` | Dashboard UI, agent types, layout |

## Workflow

### Step 0: Choose Interaction Style (FIRST ACTION)

**Before doing anything else**, unless the user has already stated a clear intent
(e.g. "configure Vertex AI", "enable paranoid mode"), ask the user how they want
to proceed using `AskUserQuestion`:

- **Conversational** — free-form natural language back-and-forth
- **Guided menu** — multiple-choice menus driving them through the configuration

If the user's first message already contains a specific configuration request,
skip this step and go straight to Step 1 (intent is clear). The choice question
is only for ambiguous "help me configure LINCE" openings.

When in **guided menu** mode, use `AskUserQuestion` at every decision point
(area to configure, specific option, confirmation) rather than free-text prompts.
When in **conversational** mode, ask open questions and infer intent.

**Language**: Match the language the user is using in the current session. Do not
hardcode a language in the skill — if they write in Italian, respond in Italian;
if English, respond in English.

### Step 1: Understand Intent

Listen to what the user wants. Common intents:

| User says | They want |
|-----------|-----------|
| "Configure Vertex AI" / "Add a provider" | Add/edit a provider (env-var bundle) |
| "Use paranoid mode" / "Increase security" | Change sandbox level or security settings |
| "Add API key for..." | Configure a provider env section |
| "Change default agent" | Set dashboard.default_agent_type |
| "Allow git push" / "Less restrictive" | Modify security settings |
| "Configure Codex" / "Add Gemini" | Agent-specific setup |
| "Show my config" / "What's configured?" | Read and present current config |
| "Fix this error" / "Something's broken" | Run check + diagnose |
| "What sandbox level should I use?" | Explain levels, help choose |

### Step 2: Read Current State

Before making changes, always check the current configuration:

```bash
lince-config list --json                          # all sections
lince-config list providers --json                # existing providers
lince-config get <relevant.key> --json            # specific value
lince-config check --json                         # any issues?
```

### Step 2: Consult Documentation

Load the relevant reference file for detailed field docs:

| Topic | Reference File |
|-------|---------------|
| Sandbox config keys | [references/sandbox-config.md](references/sandbox-config.md) |
| Dashboard config keys | [references/dashboard-config.md](references/dashboard-config.md) |
| Sandbox levels explained | [references/sandbox-levels.md](references/sandbox-levels.md) |
| Provider setup | [references/providers.md](references/providers.md) |
| Security model | [references/security.md](references/security.md) |

Load the reference ONLY when you need details you don't already know. The most common
operations are documented inline below.

### Step 3: Make Changes

Use `lince-config set` / `append` / `unset` with `-q` for clean output. Make changes
one at a time, in logical order.

### Step 4: Verify

After changes, always verify:

```bash
lince-config check --json
lince-config validate --json
lince-config get <changed.key> --json              # confirm the value
```

### Step 5: Explain

Tell the user what was changed and why, in plain language. Mention any warnings
from `check` and suggest follow-up actions.

## Common Operations

### Add a Provider (env-var bundle)

Providers are named env-var bundles that switch model provider/account.

**Anthropic Direct API:**
```bash
lince-config set providers.anthropic.description "Anthropic Direct API" -q
lince-config set providers.anthropic.env.ANTHROPIC_API_KEY "sk-ant-..." -q
```

**Vertex AI for Claude:**
```bash
lince-config set claude.providers.vertex.description "Vertex AI" -q
lince-config set claude.providers.vertex.env.CLAUDE_CODE_USE_VERTEX "1" -q
lince-config set claude.providers.vertex.env.ANTHROPIC_VERTEX_PROJECT_ID "<project-id>" -q
lince-config set claude.providers.vertex.env.ANTHROPIC_VERTEX_REGION "us-east5" -q
```

**Z.AI / GLM:**
```bash
lince-config set providers.zai.description "Z.AI / GLM" -q
lince-config set providers.zai.env.OPENAI_API_KEY "$ZAI_API_KEY" -q
lince-config set providers.zai.env.OPENAI_BASE_URL "https://open.bigmodel.cn/api/paas/v4" -q
```

**Set as default:**
```bash
lince-config set sandbox.default_provider "<name>" -q
```

### Configure Security / Sandbox Level

**Enable paranoid (kernel network isolation + credential proxy):**
```bash
lince-config set security.unshare_net true -q
lince-config set security.credential_proxy true -q
```

**Add network allowlist entries:**
```bash
lince-config append security.allow_domains "pypi.org" -q
lince-config append security.allow_domains "files.pythonhosted.org" -q
```

**Disable git push blocking (per-project only!):**
```bash
# In project-local .agent-sandbox/config.toml:
lince-config set security.block_git_push false -q
```

**Enable session logging:**
```bash
lince-config set logging.enabled true -q
lince-config set logging.dir "~/.agent-sandbox/logs" -q
```

### Configure an Agent

**Change default agent args:**
```bash
lince-config set agents.codex.default_args '["--full-auto", "--model", "o4-mini"]' -q
```

**Add home directory access:**
```bash
lince-config append agents.claude.home_ro_dirs ".config/gcloud" -q
lince-config append agents.codex.home_rw_dirs ".codex" -q
```

### Dashboard Settings

**Default agent type:**
```bash
lince-config set dashboard.default_agent_type "claude" --target dashboard -q
```

**Agent layout (floating/tiled):**
```bash
lince-config set dashboard.agent_layout "tiled" --target dashboard -q
```

**Max concurrent agents:**
```bash
lince-config set dashboard.max_agents 12 --target dashboard -q
```

### Remove a Provider

```bash
lince-config unset providers.vertex -q
# If it was the default, clear that too:
lince-config get sandbox.default_provider --json
lince-config set sandbox.default_provider "" -q
```

## Sandbox Levels Quick Reference

| Level | Network | Filesystem | Use When |
|-------|---------|------------|----------|
| `paranoid` | Kernel-isolated, proxy only | Scratch home dirs | Untrusted input, unfamiliar repos |
| `normal` | Open (inherited) | Standard mounts | Daily work (default) |
| `permissive` | Open | + gh CLI, cache, known_hosts | Need PRs/GitHub from agent |

Selected per run: `agent-sandbox run --sandbox-level paranoid`
Or per agent in dashboard config: `sandbox_level = "paranoid"`

## Provider Naming

Providers can be top-level (`[providers.<name>]`) or agent-specific
(`[<agent>.providers.<name>]`). Agent-specific providers override top-level
for that agent only. If both exist for the same name, the agent-specific one wins.

```bash
# Top-level (shared by all agents):
lince-config set providers.openai.description "OpenAI" -q

# Agent-specific (claude only):
lince-config set claude.providers.vertex.description "Vertex AI" -q
```

## Security Notes

- **Never display full API keys in conversation.** If reading a provider env that
  contains a key, mask it (show first 8 chars + "...").
- API keys in TOML are fine — the file should be `chmod 600`. `lince-config check`
  warns if permissions are too open.
- The `$VAR` syntax in env values means "resolve from host at spawn time" — tell
  the user they can use literal values or `$VAR` references.
- When the user sets `security.unshare_net = true`, always remind them that
  `security.credential_proxy = true` is also needed (paranoid mode).

## Important Rules

1. **Never edit TOML files directly** — always use `lince-config` CLI
2. **Always read before writing** — check current state first
3. **Always verify after writing** — run `check` and `validate`
4. **Mask API keys** when displaying config values
5. **Use `-q` for writes** during guided setup
6. **Use `--json` for reads** to parse programmatically
7. **Explain in plain language** what each change does
8. **Suggest follow-ups** — e.g. "Now run `agent-sandbox check`" or "Restart the dashboard to apply"
