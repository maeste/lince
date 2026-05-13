# Configuration Schema Reference

Complete field reference for agent-sandbox and lince-dashboard configuration files.

---

## Sandbox Config: `~/.agent-sandbox/config.toml`

Agent definitions live under `[agents.<name>]` sections.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | string | yes | - | Binary name to execute (must be in PATH) |
| `default_args` | list[string] | no | `[]` | Default CLI arguments appended to every invocation |
| `env` | dict | no | `{}` | Environment variables to set. Use `$VAR` syntax for expansion from host env |
| `home_ro_dirs` | list[string] | no | `[]` | Home subdirectories to bind read-only (relative to `~`, e.g. `.codex`) |
| `home_rw_dirs` | list[string] | no | `[]` | Home subdirectories to bind read-write (relative to `~`) |
| `bwrap_conflict` | bool | no | `false` | Set `true` if the agent uses bwrap internally (causes nesting conflict) |
| `disable_inner_sandbox_args` | list[string] | no | `[]` | CLI args to disable the agent's own sandbox when `bwrap_conflict = true` |

### Example

```toml
[agents.codex]
command = "codex"
default_args = ["--full-auto"]
env = { OPENAI_API_KEY = "$OPENAI_API_KEY" }
home_ro_dirs = [".codex"]
home_rw_dirs = []
bwrap_conflict = true
disable_inner_sandbox_args = ["--no-sandbox"]
```

---

## Dashboard Config: `~/.agent-sandbox/agents-defaults.toml`

Agent type definitions are top-level tables `[<name>]` (not nested under `[agents.]`).
Users can override any agent type by adding `[agents.<name>]` in their `config.toml`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | list[string] | yes | - | Command template. Supports `{agent_id}`, `{project_dir}`, `{profile}` placeholders |
| `display_name` | string | yes | - | Full name shown in dashboard UI (e.g. "OpenAI Codex") |
| `short_label` | string | yes | - | 3-character label for the table column header (e.g. "CDX") |
| `color` | string | yes | - | ANSI color name for the agent type indicator |
| `sandboxed` | bool | no | `true` | Whether the agent runs inside the bwrap sandbox |
| `has_native_hooks` | bool | no | `false` | Agent sends its own status events (true only for Claude Code) |
| `pane_title_pattern` | string | yes | - | Substring to match Zellij pane titles for agent detection |
| `status_pipe_name` | string | no | `"lince-status"` | Zellij pipe name for receiving status events |
| `env_vars` | dict | no | `{}` | Environment variables passed to the agent process |
| `home_ro_dirs` | list[string] | no | `[]` | Read-only bind mounts from `$HOME` (use `~/` prefix) |
| `home_rw_dirs` | list[string] | no | `[]` | Read-write bind mounts from `$HOME` |
| `bwrap_conflict` | bool | no | `false` | Agent uses bwrap internally, conflicts with outer sandbox |
| `disable_inner_sandbox_args` | list[string] | no | `[]` | Args to disable the agent's inner sandbox when `bwrap_conflict = true` |
| `event_map` | dict | no | `{}` | Custom mapping from agent event names to lince status strings |

### Example

```toml
[codex]
command = ["agent-sandbox", "run", "-a", "codex", "-p", "{project_dir}"]
display_name = "OpenAI Codex"
short_label = "CDX"
color = "cyan"
sandboxed = true
has_native_hooks = false
pane_title_pattern = "codex"
status_pipe_name = "lince-status"
bwrap_conflict = true
disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]
home_ro_dirs = ["~/.codex/"]

[codex.env_vars]
OPENAI_API_KEY = "$OPENAI_API_KEY"
```

---

## Valid Colors

The `color` field accepts these ANSI color names:

| Color | Typical Use |
|-------|-------------|
| `red` | Warnings, unsandboxed agents |
| `green` | Available, healthy |
| `yellow` | Caution, pending |
| `blue` | Default (Claude Code) |
| `magenta` | Alternative agents |
| `cyan` | Secondary agents (Codex) |
| `white` | Neutral |

---

## Pipe Name Conventions

| Pipe Name | Usage |
|-----------|-------|
| `claude-status` | Reserved for Claude Code. Carries rich status events (tool use, tokens, subagents) via native hooks |
| `lince-status` | Standard pipe for all other agents. Uses lince-agent-wrapper for basic start/stop events |

Agents with `has_native_hooks = true` send their own structured status events.
Agents with `has_native_hooks = false` rely on lince-agent-wrapper, which:
- Sends a `start` event when the agent process launches
- Sends a `stopped` event when the agent process exits
- Does not interfere with the agent's stdin/stdout

---

## bwrap Conflict Patterns

Some agents use bwrap (or similar container tools) internally. When agent-sandbox
also uses bwrap to sandbox the agent, nesting conflicts occur. The solution:

1. Set `bwrap_conflict = true` in the agent config
2. Provide `disable_inner_sandbox_args` to turn off the agent's internal sandbox
3. The outer agent-sandbox bwrap provides the actual sandboxing

### Known Patterns

| Agent | Internal Sandbox | Disable Args |
|-------|-----------------|--------------|
| Codex | bwrap | `["--no-sandbox"]` (sandbox config) / `["--sandbox", "danger-full-access"]` (dashboard config) |
| Gemini | Docker | `["--sandbox", "none"]` |
| Claude Code | None | N/A (`bwrap_conflict = false`) |
| Aider | None | N/A (`bwrap_conflict = false`) |
| OpenCode | None | N/A (`bwrap_conflict = false`) |

---

## Command Template Placeholders

The dashboard `command` field supports these placeholders, replaced at runtime:

| Placeholder | Description | Example Value |
|-------------|-------------|---------------|
| `{agent_id}` | Unique agent identifier assigned by the dashboard | `agent-1` |
| `{project_dir}` | Absolute path to the project directory | `/home/user/project/foo` |
| `{profile}` | Sandbox profile name (from wizard selection) | `anthropic` |

### Typical Command Templates

```toml
# Sandboxed agent via agent-sandbox
command = ["agent-sandbox", "run", "-a", "<key>", "-p", "{project_dir}"]

# Sandboxed with profile
command = ["agent-sandbox", "run", "-a", "<key>", "-p", "{project_dir}", "-P", "{profile}"]

# Unsandboxed agent (direct execution)
command = ["env", "LINCE_AGENT_ID={agent_id}", "<binary>"]

# Agent with specific args
command = ["<binary>", "--arg1", "--arg2"]
```

---

## Config File Locations

| File | Purpose | Format |
|------|---------|--------|
| `~/.agent-sandbox/config.toml` | Sandbox config + user agent overrides | `[agents.<name>]` sections |
| `~/.agent-sandbox/agents-defaults.toml` | Dashboard agent type defaults | Top-level `[<name>]` sections |
| `~/.config/lince-dashboard/config.toml` | Dashboard UI settings | `[dashboard]` section |
