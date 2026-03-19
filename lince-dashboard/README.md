# LINCE Dashboard

Multi-agent TUI dashboard for managing Claude Code instances in [Zellij](https://zellij.dev). A WASM plugin that lets you spawn, monitor, and switch between multiple Claude Code agents — all from one terminal pane.

## Overview

```
┌───────────────────────────────────────────────┐
│ LINCE Dashboard  (3 agents)                   │
├───┬────────────┬─────────┬─────────┬──────────┤
│ # │ Name       │ Profile │ Project │ Status   │
├───┼────────────┼─────────┼─────────┼──────────┤
│ 1 │ agent-1    │ vertex  │ backend │ Running  │
│>2 │ agent-2    │         │ frontend│ INPUT    │
│ 3 │ agent-3    │ zai     │ tests   │ Running  │
├───┴────────────┴─────────┴─────────┴──────────┤
│ [n]ew  [f]ocus  [h]ide  [k]ill  [i]nput      │
├───────────────────┬───────────────────────────┤
│ VoxCode (PTT)     │ Shell                     │
└───────────────────┴───────────────────────────┘
```

Agents run inside the existing [claude-sandbox](../sandbox/) — the dashboard only manages pane lifecycle, not isolation.

## Prerequisites

- **Zellij** >= 0.40 (0.43.x recommended)
- **Rust** with `wasm32-wasip1` target (`rustup target add wasm32-wasip1`)
- **Claude Code** with hooks support
- **[claude-sandbox](../sandbox/)** installed and configured
- **VoxCode** (optional, for voice relay)

## Installation

```bash
cd lince-dashboard
chmod +x install.sh
./install.sh
```

The installer:
1. Checks prerequisites (Zellij, Rust, WASM target)
2. Builds the plugin (Rust → WASM, ~900 KB)
3. Copies plugin to `~/.config/zellij/plugins/`
4. Installs layouts to `~/.config/zellij/layouts/`
5. Creates config at `~/.config/lince-dashboard/config.toml`
6. Installs Claude Code status hooks
7. Adds `zd` shell alias

After installation:

```bash
source ~/.bashrc
zd                # launch the dashboard
```

## Configuration

Edit `~/.config/lince-dashboard/config.toml`:

```toml
[dashboard]
# Default sandbox profile for new agents (empty = no -P flag)
# default_profile = ""

# Default working directory for new agents
# default_project_dir = ""

# Path to claude-sandbox command
sandbox_command = "claude-sandbox"

# Agent pane layout: "single" (just agent) or "multi" (agent + backlog + shell)
agent_layout = "single"

# How to show agent pane: "floating" (overlay) or "replace" (tab switch)
focus_mode = "floating"

# Status detection: "pipe" (zellij pipe, recommended) or "file" (/tmp polling)
status_method = "pipe"

# Directory for status files (when using file method)
status_file_dir = "/tmp"

# Maximum concurrent agents
max_agents = 8
```

## Keybindings

| Key | Action |
|-----|--------|
| `n` | Spawn new agent with default settings |
| `k` | Kill (stop) the selected agent |
| `f` / `Enter` | Focus: show the selected agent's pane |
| `h` / `Esc` | Hide: hide the focused agent's pane |
| `j` / `Down` | Select next agent in list |
| `Up` | Select previous agent in list |
| `]` | Focus next agent directly |
| `[` | Focus previous agent directly |
| `i` | Enter input mode (type to agent) |
| `Esc` (in input mode) | Exit input mode |

## Agent Lifecycle

1. Press `n` → dashboard spawns a floating pane running `claude-sandbox run`
2. Pane is hidden by default — agent appears in the dashboard table as "Starting"
3. Claude Code hooks report status via Zellij pipe → dashboard updates to "Running"
4. When Claude needs input → status shows "INPUT" (bold yellow, attention-grabbing)
5. Press `f` to show the agent's pane, interact, press `h` to hide it back
6. Press `k` to kill the agent and close its pane

## Voice Relay

VoxCode runs in the fixed bottom-left pane. When configured to use pipe mode, transcribed text is sent to the dashboard plugin which forwards it to the active agent:

```
VoxCode → zellij pipe --name "voxcode-text" → Dashboard Plugin → agent pane
```

Target priority:
1. Focused agent (if one is shown)
2. Selected agent (highlighted in table)
3. No agent → error message in command bar

## Status Detection

### Pipe mode (default, recommended)

Claude Code hooks send status via `zellij pipe`:

```bash
zellij pipe --name "claude-status" --payload '{"agent_id":"agent-1","event":"idle"}'
```

Events: `stopped`, `running`, `idle`, `permission`

### File mode (fallback)

Hooks write status to `/tmp/claude-{agent_id}.state`. The plugin polls every 2 seconds.

Set `status_method = "file"` in config to use this mode.

## Architecture

```
lince-dashboard/
├── plugin/
│   ├── Cargo.toml              # Rust WASM crate
│   ├── build.sh                # Build → .wasm
│   └── src/
│       ├── lib.rs              # Plugin entry, key handling, pipe dispatch
│       ├── config.rs           # TOML config parsing
│       ├── types.rs            # AgentInfo, AgentStatus, StatusMessage
│       ├── dashboard.rs        # TUI rendering (ANSI)
│       ├── agent.rs            # Agent spawn/stop/tracking
│       └── pane_manager.rs     # Pane focus/hide/show
├── hooks/
│   ├── claude-status-hook.sh   # Claude Code hook → pipe + file
│   └── install-hooks.sh        # Hook installer
├── layouts/
│   ├── dashboard.kdl           # Main layout (plugin + voxcode + shell)
│   ├── agent-single.kdl        # Reference: single floating pane
│   └── agent-multi.kdl         # Template: agent + backlog + shell tab
├── config.toml                 # Default configuration
├── install.sh                  # Interactive installer
└── README.md
```

### Plugin API usage

| Zellij API | Purpose |
|------------|---------|
| `open_command_pane_floating()` | Spawn agent panes |
| `hide_pane_with_id()` / `show_pane_with_id()` | Toggle pane visibility |
| `focus_terminal_pane()` | Focus a specific pane |
| `close_terminal_pane()` | Kill agent panes |
| `write_chars_to_pane_id()` | Forward voice text to agent |
| `PaneUpdate` event | Track pane lifecycle |
| `pipe()` method | Receive status + voice messages |

## Sandbox Integration

For hooks to work inside `claude-sandbox`, the sandbox must pass through Zellij environment variables. Add to your sandbox config (`~/.claude-sandbox/config.toml`):

```toml
[env]
passthrough = ["ZELLIJ", "ZELLIJ_SESSION_NAME", "LINCE_AGENT_ID"]
```

## Troubleshooting

### Plugin won't load
- Check the WASM file exists: `ls ~/.config/zellij/plugins/lince-dashboard.wasm`
- Verify Zellij version: `zellij --version` (need >= 0.40)
- Check layout path: `zellij --layout ~/.config/zellij/layouts/dashboard.kdl`
- Grant permissions when Zellij prompts

### Status not updating
- Verify hooks are installed: check `~/.claude/settings.json` for `hooks` section
- Test hook manually: `echo '{"hook_event_name":"Stop"}' | LINCE_AGENT_ID=test-1 bash ~/.local/bin/claude-status-hook.sh`
- Check file fallback: `cat /tmp/claude-test-1.state`
- Ensure sandbox passes env vars (see Sandbox Integration above)

### Agent panes not hiding
- This is a known Zellij behavior — `hide_pane_with_id` requires `ChangeApplicationState` permission
- The plugin requests this permission on load; accept the permission prompt

### Voice relay not working
- VoxCode must send via pipe: `zellij pipe --name "voxcode-text" --payload "text"`
- Check an agent is selected/focused in the dashboard
- Test manually: `zellij pipe --name "voxcode-text" --payload "hello"`
