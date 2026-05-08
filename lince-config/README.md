# lince-config

Structured CLI for reading and editing LINCE configuration files.

## What it does

`lince-config` is the programmatic interface between natural-language skills (or power users) and LINCE's TOML config files. It reads and writes both sandbox (`~/.agent-sandbox/config.toml`) and dashboard (`~/.config/lince-dashboard/config.toml`) configurations, preserving comments and formatting.

## Install

```bash
cd lince-config && ./install.sh
```

Requires Python 3.11+ and `tomlkit` (auto-installed by `install.sh`).

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
lince-config validate [--target sandbox|dashboard] [--json]
```

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
