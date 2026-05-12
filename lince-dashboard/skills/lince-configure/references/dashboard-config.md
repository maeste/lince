# Dashboard Configuration Reference

Quick reference for `~/.config/lince-dashboard/config.toml`. Loaded by `lince-config --target dashboard`.

## [dashboard]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_provider` | str | `""` | Default provider for new agents |
| `sandbox_config_path` | str | `"~/.agent-sandbox/config.toml"` | Path to sandbox config |
| `default_project_dir` | str | `""` | Default working dir (empty = cwd) |
| `sandbox_command` | str | `"agent-sandbox"` | Path to agent-sandbox binary |
| `agent_layout` | str | `"floating"` | `"floating"` or `"tiled"` |
| `focus_mode` | str | `"floating"` | `"floating"` or `"replace"` |
| `status_method` | str | `"pipe"` | `"pipe"` (recommended) or `"file"` |
| `status_file_dir` | str | `"/tmp/lince-dashboard"` | Dir for status files (file mode) |
| `max_agents` | int | `9` | Max concurrent agents |
| `sandbox_backend` | str | `"auto"` | `"auto"`, `"agent-sandbox"`, or `"nono"` |
| `default_agent_type` | str | `"claude"` | Default agent type for new agents |

## [dashboard.sandbox_colors]

Customize wizard colors per sandbox level:

```toml
[dashboard.sandbox_colors]
paranoid = "green"
normal = "blue"
permissive = "yellow"
default = "white"
```

Valid colors: red, green, yellow, blue, magenta, cyan, white.

## [agents.\<name\>] — Agent Type Overrides

Override shipped presets or define custom agents. Full replacement (no per-field merge).

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `command` | list | Yes | Command template with `{agent_id}`, `{project_dir}`, `{provider}` |
| `pane_title_pattern` | str | Yes | Pattern to match pane titles |
| `status_pipe_name` | str | Yes | Zellij pipe name |
| `display_name` | str | Yes | Full name in UI |
| `short_label` | str | Yes | 3-char label |
| `color` | str | Yes | ANSI color: red/green/yellow/blue/magenta/cyan/white |
| `sandboxed` | bool | Yes | Run inside sandbox |
| `has_native_hooks` | bool | No | `true` only for Claude Code |
| `bwrap_conflict` | bool | No | Agent uses bwrap internally |
| `disable_inner_sandbox_args` | list | No | Args to disable inner sandbox |
| `providers` | list | No | `["__discover__"]`, `[]`, or explicit list |
| `home_ro_dirs` | list | No | Read-only bind mounts |
| `home_rw_dirs` | list | No | Read-write bind mounts |
| `env_vars` | dict | No | Env vars ($VAR expansion) |
| `event_map` | dict | No | Custom event→status mapping |
| `sandbox_backend` | str | No | Per-agent backend override |
| `sandbox_level` | str | No | `"paranoid"`, `"normal"`, `"permissive"`, or custom |

## Hot-Reload

These settings apply immediately (no restart):
- `focus_mode`, `status_method`, `max_agents`, `agent_layout`, `default_provider`, `default_project_dir`

Requires restart:
- `sandbox_command`

## agents-defaults.toml

Shipped presets at `~/.agent-sandbox/agents-defaults.toml`. Overwritten on updates.
Customize in `config.toml` instead.

Default agent types: claude, claude-unsandboxed, codex, gemini, opencode, pi.
