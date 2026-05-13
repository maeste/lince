# Agent Configuration Examples

Real-world agent configurations from the lince ecosystem.

---

## Sandbox Preset Configs (`~/.agent-sandbox/config.toml`)

These are the built-in agent definitions from `agents-defaults.toml` in agent-sandbox.

### Claude Code

```toml
[agents.claude]
command = "claude"
default_args = ["--dangerously-skip-permissions"]
env = {}
home_ro_dirs = []
home_rw_dirs = []
bwrap_conflict = false
disable_inner_sandbox_args = []
```

### OpenAI Codex

```toml
[agents.codex]
command = "codex"
default_args = ["--full-auto"]
env = {}
home_ro_dirs = [".codex"]
home_rw_dirs = []
bwrap_conflict = true
disable_inner_sandbox_args = ["--no-sandbox"]
```

### Google Gemini CLI

```toml
[agents.gemini]
command = "gemini"
default_args = []
env = {}
home_ro_dirs = [".gemini"]
home_rw_dirs = []
bwrap_conflict = false
disable_inner_sandbox_args = []
```

### Aider

```toml
[agents.aider]
command = "aider"
default_args = []
env = {}
home_ro_dirs = [".aider"]
home_rw_dirs = []
bwrap_conflict = false
disable_inner_sandbox_args = []
```

### Amp

```toml
[agents.amp]
command = "amp"
default_args = []
env = {}
home_ro_dirs = [".amplication"]
home_rw_dirs = []
bwrap_conflict = false
disable_inner_sandbox_args = []
```

---

## Dashboard Preset Configs (`~/.agent-sandbox/agents-defaults.toml`)

These are the built-in dashboard agent type definitions.

### Claude Code (sandboxed)

```toml
[claude]
command = ["agent-sandbox", "run", "-p", "{project_dir}", "--id", "{agent_id}"]
pane_title_pattern = "agent-sandbox"
status_pipe_name = "claude-status"
display_name = "Claude Code"
short_label = "CLA"
color = "blue"
sandboxed = true
has_native_hooks = true
home_ro_dirs = ["~/.claude/"]
```

### Claude Code (unsandboxed)

```toml
[claude-unsandboxed]
command = ["env", "LINCE_AGENT_ID={agent_id}", "claude"]
pane_title_pattern = "claude"
status_pipe_name = "claude-status"
display_name = "Claude Code (unsandboxed)"
short_label = "CLU"
color = "red"
sandboxed = false
has_native_hooks = true
```

### OpenAI Codex

```toml
[codex]
command = ["codex", "--full-auto"]
pane_title_pattern = "codex"
status_pipe_name = "lince-status"
display_name = "OpenAI Codex"
short_label = "CDX"
color = "cyan"
sandboxed = true
has_native_hooks = false
bwrap_conflict = true
disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]
home_ro_dirs = ["~/.codex/"]

[codex.env_vars]
OPENAI_API_KEY = "$OPENAI_API_KEY"
```

### Google Gemini CLI

```toml
[gemini]
command = ["gemini"]
pane_title_pattern = "gemini"
status_pipe_name = "lince-status"
display_name = "Google Gemini CLI"
short_label = "GEM"
color = "yellow"
sandboxed = true
has_native_hooks = false
disable_inner_sandbox_args = ["--sandbox", "none"]
home_ro_dirs = ["~/.gemini/"]

[gemini.env_vars]
GEMINI_API_KEY = "$GEMINI_API_KEY"
```

### OpenCode

```toml
[opencode]
command = ["opencode"]
pane_title_pattern = "opencode"
status_pipe_name = "lince-status"
display_name = "OpenCode"
short_label = "OPC"
color = "green"
sandboxed = true
has_native_hooks = false
home_ro_dirs = ["~/.config/opencode/"]
```

---

## Custom Agent Example

Here is a complete example for registering a hypothetical agent called "kiro":

### Sandbox config (append to `~/.agent-sandbox/config.toml`)

```toml
[agents.kiro]
command = "kiro"
default_args = ["--headless"]
env = { AWS_ACCESS_KEY_ID = "$AWS_ACCESS_KEY_ID", AWS_SECRET_ACCESS_KEY = "$AWS_SECRET_ACCESS_KEY" }
home_ro_dirs = [".kiro"]
home_rw_dirs = []
bwrap_conflict = false
disable_inner_sandbox_args = []
```

### Dashboard config (append to `~/.agent-sandbox/agents-defaults.toml`)

```toml
[kiro]
command = ["agent-sandbox", "run", "-a", "kiro", "-p", "{project_dir}"]
display_name = "Kiro"
short_label = "KIR"
color = "magenta"
sandboxed = true
has_native_hooks = false
pane_title_pattern = "kiro"
status_pipe_name = "lince-status"
home_ro_dirs = ["~/.kiro/"]

[kiro.env_vars]
AWS_ACCESS_KEY_ID = "$AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "$AWS_SECRET_ACCESS_KEY"
```

---

## Key Differences Between Sandbox and Dashboard Configs

| Aspect | Sandbox (`config.toml`) | Dashboard (`agents-defaults.toml`) |
|--------|------------------------|-----------------------------------|
| Section format | `[agents.<name>]` | `[<name>]` (top-level) |
| `command` type | string (binary name) | list[string] (full command template) |
| `env` field name | `env` | `env_vars` |
| `home_ro_dirs` format | Relative to `~` (e.g. `.codex`) | With `~/` prefix (e.g. `~/.codex/`) |
| Extra UI fields | N/A | `display_name`, `short_label`, `color`, `pane_title_pattern`, `status_pipe_name` |
| `has_native_hooks` | N/A | Required (set `false` for non-Claude agents) |
| `event_map` | N/A | Optional custom event-to-status mapping |
