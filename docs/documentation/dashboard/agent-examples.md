# Agent Examples

Preset agent types, configuration patterns, and examples for adding custom agents to the LINCE Dashboard.

## Default Agent Types

The following agent types ship in `agents-defaults.toml` and are available in the wizard out of the box.

| Key | Display Name | Short | Sandboxed | Backend | Native Hooks | Notes |
|-----|-------------|-------|-----------|---------|--------------|-------|
| `claude` | Claude Code | CLA | Yes | agent-sandbox | Yes | Default. Rich status via `claude-status` pipe. |
| `claude-unsandboxed` | Claude Code (unsandboxed) | CLU | No | -- | Yes | Red `CLU!` label. Supports profile-based provider switching. |
| `claude-nono` | Claude Code (nono) | CLA | Yes | nono | Yes | Landlock/Seatbelt sandbox. |
| `codex` | OpenAI Codex (unsandboxed) | CDX | No | -- | No | Runs with Codex's own sandbox. |
| `codex-bwrap` | OpenAI Codex (sandboxed) | CDX | Yes | agent-sandbox | No | bwrap isolation. `bwrap_conflict` handled automatically. |
| `codex-nono` | OpenAI Codex (nono) | CDX | Yes | nono | No | Landlock/Seatbelt sandbox. |
| `gemini` | Google Gemini CLI | GEM | No | -- | No | Runs directly without sandbox. |
| `gemini-bwrap` | Google Gemini CLI (sandboxed) | GEM | Yes | agent-sandbox | No | bwrap isolation. |
| `gemini-nono` | Google Gemini CLI (nono) | GEM | Yes | nono | No | Landlock/Seatbelt sandbox. |
| `opencode` | OpenCode | OPC | No | -- | No | Runs directly without sandbox. |
| `opencode-bwrap` | OpenCode (sandboxed) | OPC | Yes | agent-sandbox | No | bwrap isolation. |
| `opencode-nono` | OpenCode (nono) | OPC | Yes | nono | No | Landlock/Seatbelt sandbox. |

## Understanding the Variants

Most agents come in up to three variants: **direct**, **-bwrap**, and **-nono**.

- **Direct** (e.g. `codex`, `gemini`) runs the agent binary as-is, relying on whatever sandbox the agent provides natively -- or no sandbox at all.
- **-bwrap** (e.g. `codex-bwrap`, `gemini-bwrap`) wraps the agent inside `agent-sandbox` using bubblewrap for filesystem isolation. Linux only.
- **-nono** (e.g. `codex-nono`, `gemini-nono`) wraps the agent inside `nono` using Landlock (Linux) or Seatbelt (macOS) for filesystem isolation. Cross-platform.

Choose `-bwrap` or `-nono` when you want LINCE-managed isolation regardless of the agent's own sandbox capabilities.

## Unsandboxed Mode

Agents with `sandboxed = false` run without any LINCE-managed isolation. The dashboard makes this visually obvious:

- A red `!` suffix on the type label in every table row (e.g. `CLU!`).
- A red `[NON-SANDBOXED]` tag in the Zellij pane title.
- A red `[NON-SANDBOXED]` warning in the detail panel.

Use unsandboxed mode only in trusted environments where sandbox restrictions are impractical. Unsandboxed agents still support profiles for provider selection -- the dashboard uses `env -u VAR1 VAR2=val ...` to set and unset environment variables cleanly.

## Adding a Custom Agent

### Automatic: /lince-setup Skill

The easiest way to add a new agent is the `/lince-setup` skill. Run the target agent outside the dashboard, invoke `/lince-setup`, and the agent describes its own requirements. The skill generates correct TOML for both sandbox and dashboard configs.

See the [Multi-Agent Guide](https://github.com/RisorseArtificiali/lince/blob/main/lince-dashboard/MULTI-AGENT-GUIDE.md) for the full flow and examples.

### Manual Configuration

To add a custom agent manually:

1. Choose a unique key (lowercase, hyphens allowed).
2. Add an `[agents.<key>]` section to `~/.config/lince-dashboard/config.toml`.
3. Set the required fields: `command`, `pane_title_pattern`, `status_pipe_name`, `display_name`, `short_label`, `color`, `sandboxed`.
4. Optionally set `has_native_hooks`, `env_vars`, `home_ro_dirs`, `profiles`, etc.
5. Restart the dashboard. The new type appears in the wizard.

No code changes or recompilation required.

## Example: Simple Bash Agent

A minimal custom agent that runs a bash automation script inside the sandbox.

**Dashboard config** (`~/.config/lince-dashboard/config.toml`):

```toml
[agents.bash-helper]
command = ["agent-sandbox", "run", "-a", "bash", "-p", "{project_dir}", "--id", "{agent_id}"]
pane_title_pattern = "bash"
status_pipe_name = "lince-status"
display_name = "Bash Helper"
short_label = "BSH"
color = "white"
sandboxed = true
has_native_hooks = false
```

Since `has_native_hooks = false`, the dashboard automatically wraps the command with `lince-agent-wrapper` to provide `start` and `stopped` lifecycle events.

In the wizard, this agent appears as:

```
  > Bash Helper (bash-helper)
```

After spawning, the table shows:

```
 1  BSH  bash-agent-1      Running
```

## Example: Agent with Multiple Providers

Claude Code can connect to different providers (Anthropic direct, Vertex AI, etc.) using profiles. This example shows how to configure provider switching for both sandboxed and unsandboxed modes.

**Sandbox profiles** (`~/.agent-sandbox/config.toml`):

```toml
[profiles.anthropic]
description = "Anthropic Direct API"
env_unset = ["CLAUDE_CODE_USE_VERTEX", "CLOUD_ML_REGION"]

[profiles.anthropic.env]
ANTHROPIC_API_KEY = "sk-ant-..."

[profiles.vertex]
description = "Vertex AI"
env_unset = ["ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"]

[profiles.vertex.env]
CLAUDE_CODE_USE_VERTEX = "1"
CLOUD_ML_REGION = "us-east5"
```

**Dashboard config** for the unsandboxed variant (`~/.config/lince-dashboard/config.toml`):

```toml
[agents.claude-unsandboxed]
command = ["claude"]
pane_title_pattern = "claude"
status_pipe_name = "claude-status"
display_name = "Claude Code (unsandboxed)"
short_label = "CLU"
color = "red"
sandboxed = false
has_native_hooks = true
profiles = ["__discover__"]
```

The `env_unset` field is critical for unsandboxed agents. Because they inherit the full host environment, switching from Anthropic to Vertex requires **unsetting** `ANTHROPIC_API_KEY` before **setting** `CLAUDE_CODE_USE_VERTEX`. Without `env_unset`, both keys would be present and the agent could pick the wrong provider.

For sandboxed agents, `env_unset` is a no-op because `agent-sandbox` uses `--clearenv` to start from a blank environment.

## Handling bwrap Conflicts

Some agents (like Codex) use bubblewrap internally. Nesting bwrap fails. The `-bwrap` variants handle this automatically:

1. Set `bwrap_conflict = true` on the agent type.
2. Set `disable_inner_sandbox_args` to the arguments that disable the agent's internal sandbox.

```toml
[agents.codex-bwrap]
command = ["agent-sandbox", "run", "-p", "{project_dir}", "--id", "{agent_id}", "--agent", "codex"]
sandboxed = true
bwrap_conflict = true
disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]
```

The sandbox injects `--sandbox danger-full-access` into the Codex command, disabling its internal bwrap before wrapping it in the LINCE bwrap jail.

**Dry-run verification**: Always verify the final command with `--dry-run` before first use:

```bash
agent-sandbox run -a codex-bwrap -p ~/project --dry-run
# Output shows: ... codex --full-auto --sandbox danger-full-access
```

## Status Reporting

### Native Hooks

Claude Code has built-in hooks that send rich status events via the `claude-status` Zellij pipe.

**Events**: `idle`, `running`, `permission`, `subagent_start`, `subagent_stop`, `PreToolUse`, `Stop`.

**Payload fields**:

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | Unique agent identifier (e.g. `agent-1`) |
| `event` | string | Event name |
| `tool_name` | string (optional) | Active tool name (on `PreToolUse`) |
| `tokens_in` | integer (optional) | Input token count |
| `tokens_out` | integer (optional) | Output token count |
| `subagent_type` | string (optional) | Sub-agent type (on subagent events) |
| `model` | string (optional) | Model identifier |

Example payload:

```json
{"agent_id":"agent-1","event":"running","tokens_in":1200,"tokens_out":450}
```

### lince-agent-wrapper

For agents with `has_native_hooks = false`, the dashboard automatically injects `lince-agent-wrapper` around the agent command. The wrapper:

- Sends a `start` event when the agent process launches.
- Sends a `stopped` event when the agent process exits (for any reason).
- Is transparent to the agent -- does not touch stdin or stdout.

This provides basic lifecycle tracking for any agent without requiring agent-specific integration.

### Custom event_map

Agents with non-standard event names can define a mapping to LINCE status strings:

```toml
[agents.my-agent.event_map]
"agent_ready" = "idle"
"agent_working" = "running"
"agent_done" = "stopped"
"needs_approval" = "permission"
```

The left side is the event string the agent sends. The right side is one of the canonical LINCE statuses: `idle`, `running`, `stopped`, `permission`.

If an incoming event matches the `event_map`, the mapped status is used. Otherwise, the dashboard falls back to canonical name matching and then defaults to `Running`.

## See Also

- [Usage Guide](dashboard/usage-guide.md) -- how to operate the dashboard
- [Configuration Reference](dashboard/config-reference.md) -- all config keys and their defaults
- [Sandbox CLI Reference](sandbox/cli-reference.md) -- the `agent-sandbox` command
- [Multi-Agent Guide](https://github.com/RisorseArtificiali/lince/blob/main/lince-dashboard/MULTI-AGENT-GUIDE.md) -- migration guide for multi-agent support
