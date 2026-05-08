# Sandbox Configuration Reference

Quick reference for `~/.agent-sandbox/config.toml` keys. Loaded by `lince-config --target sandbox`.

## [sandbox]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `extra_rw` | list | `[]` | Extra writable dirs besides project |
| `ro_dirs` | list | `["~/project"]` | Read-only dirs |
| `persist_toolchains` | bool | `true` | Keep cargo/npm/go caches between runs |
| `auto_expose_path` | bool | `true` | Auto-detect $PATH under $HOME |
| `home_ro_dirs` | list | `[".config/gcloud"]` | Home subdirs to expose read-only |
| `default_provider` | str | `""` | Default provider name (no -P needed) |
| `backend` | str | `"auto"` | `"agent-sandbox"`, `"nono"`, or `"auto"` |

## [security]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `unshare_pid` | bool | `true` | Hide host processes |
| `new_session` | bool | `false` | New terminal session (may break Ctrl+C) |
| `block_git_push` | bool | `true` | Block via wrapper in PATH |
| `credential_proxy` | bool | `false` | Inject API keys on host side |
| `unshare_net` | bool | `false` | Kernel network isolation |
| `allow_domains` | list | `[]` | Extra hosts for credential proxy |

## [credential_proxy]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `blocked_hosts` | list | `["169.254.169.254", ...]` | Extra hosts to block |

## [git]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `strip_sections` | list | `['credential', 'url ".*"']` | Regex patterns for .gitconfig |

## [git.overrides]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `"push.default"` | str | `"nothing"` | Forces bare git push to no-op |

## [env]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `passthrough` | list | `["TERM", "COLORTERM", ...]` | Host vars to pass into sandbox |

## [env.extra]

Static key=value pairs injected via `--setenv`.

## [logging]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable transcript logging |
| `dir` | str | `"~/.agent-sandbox/logs"` | Log directory |

## [snapshot]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_project` | bool | `false` | Auto-snapshot project before each run |
| `auto_config` | bool | `true` | Auto-snapshot agent config |
| `max_project_snapshots` | int | `3` | Max project snapshots |
| `max_config_snapshots` | int | `5` | Max config snapshots |
| `project_exclude` | list | `[".git", "node_modules", ...]` | Excluded dirs |

## [claude]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `config_dir` | str | `"~/.agent-sandbox/claude-config"` | Isolated config copy |
| `use_real_config` | bool | `false` | Use real ~/.claude directly |

## [agents.\<name\>]

Per-agent overrides. Key = agent name (claude, codex, gemini, aider, opencode, amp, pi, bash).

| Key | Type | Description |
|-----|------|-------------|
| `command` | str | Binary to execute |
| `default_args` | list | CLI arguments |
| `env` | dict | Extra env vars ($VAR expansion supported) |
| `home_ro_dirs` | list | Read-only home subdirs |
| `home_rw_dirs` | list | Read-write home subdirs |
| `bwrap_conflict` | bool | Agent uses bwrap internally |
| `disable_inner_sandbox_args` | list | Args to disable agent's inner sandbox |

## Providers

### Top-level: [providers.\<name\>]

| Key | Type | Description |
|-----|------|-------------|
| `description` | str | Human-readable label |
| `env` | dict | Env vars to inject |
| `env_unset` | list | Env vars to remove (for unsandboxed) |
| `default_args` | list | Override agent default_args |

### Agent-specific: [\<agent\>.providers.\<name\>]

Same fields as top-level, scoped to one agent. Takes priority over top-level with same name.

### Legacy

`[profiles.*]` and `[<agent>.profiles.*]` still work (deprecated since gh#81).
Run `agent-sandbox migrate-providers` to rewrite.
