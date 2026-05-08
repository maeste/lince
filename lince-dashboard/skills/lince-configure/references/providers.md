# Provider Configuration Reference

Providers are named env-var bundles that switch model provider/account at runtime.

## Structure

```toml
# Top-level (shared):
[providers.<name>]
description = "Human-readable label"

[providers.<name>.env]
API_KEY_VAR = "literal-value-or-$VAR"

# Agent-specific (scoped to one agent):
[<agent>.providers.<name>]
description = "..."

[<agent>.providers.<name>.env]
API_KEY_VAR = "..."
```

## Provider Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | str | Label shown in run banner and wizard |
| `env` | dict | Env vars injected via `--setenv`. Use `$VAR` for host expansion |
| `env_unset` | list | Env vars to remove (unsandboxed agents only) |
| `default_args` | list | Override agent's default_args when this provider is active |

## Common Provider Templates

### Anthropic Direct API
```toml
[providers.anthropic]
description = "Anthropic Direct API"

[providers.anthropic.env]
ANTHROPIC_API_KEY = "sk-ant-..."
```

### Vertex AI (Claude-specific)
```toml
[claude.providers.vertex]
description = "Vertex AI"

[claude.providers.vertex.env]
CLAUDE_CODE_USE_VERTEX = "1"
ANTHROPIC_VERTEX_PROJECT_ID = "my-gcp-project"
ANTHROPIC_VERTEX_REGION = "us-east5"
```

### OpenAI Direct
```toml
[providers.openai]
description = "OpenAI Direct API"

[providers.openai.env]
OPENAI_API_KEY = "sk-..."
```

### Z.AI / GLM
```toml
[providers.zai]
description = "Z.AI / GLM"

[providers.zai.env]
OPENAI_API_KEY = "$ZAI_API_KEY"
OPENAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
```

### AWS Bedrock (Claude-specific)
```toml
[claude.providers.bedrock]
description = "AWS Bedrock"

[claude.providers.bedrock.env]
ANTHROPIC_BASE_URL = "https://bedrock-runtime.us-east-1.amazonaws.com"
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "$AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "$AWS_SECRET_ACCESS_KEY"
```

## Selecting a Provider

Default (no flag needed):
```bash
lince-config set sandbox.default_provider "vertex" -q
```

Per run:
```bash
agent-sandbox run -P vertex
agent-sandbox run --provider anthropic
```

## $VAR Syntax

Env values starting with `$` are resolved from the **host environment** at spawn time:

- `"$ANTHROPIC_API_KEY"` → reads host's ANTHROPIC_API_KEY
- `"sk-ant-literal"` → literal string

For sandboxed agents, the sandbox starts with `--clearenv`, so only declared vars are visible.
For unsandboxed agents, the full host env is inherited plus provider overrides.

## env_unset

Only relevant for **unsandboxed** agents. When switching providers, you may need to
remove conflicting vars from the inherited host environment:

```toml
[claude.providers.vertex]
description = "Vertex AI"
env_unset = ["ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"]

[claude.providers.vertex.env]
CLAUDE_CODE_USE_VERTEX = "1"
CLOUD_ML_REGION = "us-east5"
```

For sandboxed agents, `env_unset` is a no-op (environment is already clean).

## Legacy

`[profiles.*]` / `[<agent>.profiles.*]` is the legacy spelling.
Run `agent-sandbox migrate-providers` to rewrite in place.
