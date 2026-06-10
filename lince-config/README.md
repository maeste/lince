# lince-config

Structured CLI for reading and editing LINCE configuration files.

## What it does

`lince-config` is the programmatic interface between natural-language skills (or power users) and LINCE's TOML config files. It reads and writes both sandbox (`~/.agent-sandbox/config.toml`) and dashboard (`~/.config/lince-dashboard/config.toml`) configurations, preserving comments and formatting.

## Install / update / uninstall

```bash
cd lince-config && ./install.sh    # install to ~/.local/bin/lince-config
./update.sh                        # refresh after pulling new changes
./uninstall.sh                     # remove from ~/.local/bin
```

Requires Python 3.11+ and `tomlkit` (auto-installed by `install.sh` and `update.sh`).

## Commands

```bash
# Read
lince-config get <dotted.key> [--target sandbox|dashboard] [--json]
lince-config list [section]   [--target sandbox|dashboard] [--json]

# Write
lince-config set <dotted.key> <value>    [--target sandbox|dashboard] [-q]
lince-config append <dotted.key> <value> [--target sandbox|dashboard] [-q]
lince-config remove <dotted.key> <value> [--target sandbox|dashboard] [-q]
lince-config unset <dotted.key>          [--target sandbox|dashboard] [-q]

# Diagnostics
lince-config check    [--target sandbox|dashboard] [--json]
lince-config validate [--target sandbox|dashboard|lince|registry] [--file PATH] [--overlay] [--json]

# JSON Schemas (Taplo-compatible — see schemas/ in the repo)
lince-config schema <lince|registry-agent|registry-providers|sandbox-config|dashboard-config>
lince-config schema --write schemas/
```

`validate` is schema-driven (#203): type mismatches and missing required keys
are errors; unknown keys under known tables are warnings (forward-compat).
For `--target lince` (the Config v2 `~/.config/lince/lince.toml`) it also
enforces the version contract — explicit "config older/newer than supported"
errors with the fixing command named. `--target registry` validates every
`registry.d/*.toml`. `--overlay` validates a project overlay
(`<project>/.lince/lince.toml`, no `version` key required).

## Examples

```bash
# Read a value
lince-config get sandbox.default_provider
lince-config get security.unshare_net
lince-config get providers.vertex --json

# Set a value
lince-config set sandbox.default_provider "vertex"
lince-config set security.unshare_net true
lince-config set security.credential_proxy true

# Configure a provider
lince-config set claude.providers.vertex.description "Vertex AI"
lince-config set claude.providers.vertex.env.CLAUDE_CODE_USE_VERTEX "1"
lince-config set claude.providers.vertex.env.ANTHROPIC_VERTEX_PROJECT_ID "my-gcp-project"

# Manage lists
lince-config append security.allow_domains "pypi.org"
lince-config remove security.allow_domains "pypi.org"

# Remove a section
lince-config unset providers.vertex

# Diagnostics
lince-config check
lince-config validate

# Dashboard config
lince-config get dashboard.agent_layout --target dashboard
lince-config set dashboard.max_agents 16 --target dashboard
```

## Value coercion

CLI string values are auto-coerced:

| Input            | Type    |
|------------------|---------|
| `true` / `false` | bool    |
| `42`             | int     |
| `["a","b"]`      | list    |
| everything else  | string  |

## Target

- `--target sandbox` (default): operates on `~/.agent-sandbox/config.toml`
- `--target dashboard`: operates on `~/.config/lince-dashboard/config.toml`

For sandbox, project-local `.agent-sandbox/config.toml` takes priority when present.

## Skill integration

The `--json` and `-q` (quiet) flags are designed for automated use by skills:

```bash
# Skill reads current state
lince-config list providers --json -q

# Skill makes changes quietly
lince-config set providers.bedrock.description "AWS Bedrock" -q
lince-config set providers.bedrock.env.AWS_REGION "us-east-1" -q

# Skill verifies
lince-config check --json
```
