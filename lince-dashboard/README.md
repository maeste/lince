# LINCE Dashboard

Multi-agent TUI dashboard for managing Claude Code instances in [Zellij](https://zellij.dev). A WASM plugin that lets you spawn, monitor, and switch between multiple Claude Code agents — all from one terminal pane.

## Overview

```
┌───────────────────────────────────────────────────────┐
│ LINCE Dashboard  (3 agents)                           │
├───┬────────────┬──────────┬────────┬────────┬─────────┤
│ # │ Name       │ Status   │ Tokens │Profile │ Project │
├───┼────────────┼──────────┼────────┼────────┼─────────┤
│ 1 │ agent-1    │ Running  │ 1.2k/5k│ vertex │ backend │
│>2 │ agent-2    │ INPUT    │    -   │        │ frontend│
│ 3 │ agent-3    │ Running 2⚙│ 3k/12k│ zai   │ tests   │
├───┴────────────┴──────────┴────────┴────────┴─────────┤
│ [n] New [N] Wizard [f] Focus [Q] Save+Quit            │
└───────────────────────────────────────────────────────┘
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

# Agent pane layout: "floating" (overlay, default) or "tiled" (fixed in layout grid)
# Use "tiled" with layouts/dashboard-tiled.kdl for agents in a fixed split
agent_layout = "floating"

# How to show agent pane: "floating" (overlay) or "replace" (tab switch)
focus_mode = "floating"

# Status detection: "pipe" (zellij pipe, recommended) or "file" (/tmp polling)
status_method = "pipe"

# Directory for status files (when using file method)
status_file_dir = "/tmp/lince-dashboard"

# Maximum concurrent agents
max_agents = 8
```

### Config Hot-Reload

The plugin automatically detects changes to `config.toml` every 5 seconds and applies them without restart. A "Config reloaded" notification appears in the status bar.

**Hot-reloadable settings** (applied immediately):
- `focus_mode`, `status_method`, `max_agents`, `status_file_dir`
- `agent_layout`, `default_profile`, `default_project_dir`

**Not hot-reloadable** (only affects new agents after restart):
- `sandbox_command`

If the config file has a parse error, the previous working config is preserved and an error message is shown.

### Tiled Pane Layout

By default agents spawn as floating overlay panes. Set `agent_layout = "tiled"` to have agents open as tiled panes in a fixed position within the Zellij layout grid.

Use the included tiled layout for a split view (agents left, dashboard right):

```bash
zellij --layout ~/.config/zellij/layouts/dashboard-tiled.kdl
```

```
┌────────────────────┬────────────────┐
│ Agent panes (60%)  │ Dashboard (40%)│
│ (spawned by plugin)│ plugin         │
└────────────────────┴────────────────┘
```

In tiled mode:
- New agents appear as tiled panes (Zellij places them in the largest available area)
- Focus (`f`/`Enter`) switches terminal focus to the agent pane
- No show/hide toggling — tiled panes are always visible
- `h`/`Esc` returns focus to the dashboard

## Keybindings

### Normal Mode

| Key | Action |
|-----|--------|
| `n` | Show name prompt, then spawn agent with that name |
| `N` (Shift+n) | Open agent creation wizard (name, profile, directory) |
| `r` | Rename the selected agent |
| `x` | Kill (stop) the selected agent |
| `f` | Focus: show the selected agent's pane |
| `Enter` | Toggle detail panel for the selected agent |
| `h` / `Esc` | Hide: hide the focused agent's pane |
| `Q` | Save agent state to `.lince-dashboard` and quit Zellij |
| `j` / `Down` | Select next agent in list |
| `Up` | Select previous agent in list |
| `]` | Focus next agent directly |
| `[` | Focus previous agent directly |
| `i` | Toggle info/detail panel |

### Inline Name Prompt (n)

Pressing `n` shows a blue prompt bar at the bottom of the dashboard:

```
Name: my-agent█          (default: agent-3)  [Enter] OK  [Esc] Cancel
```

- Type a custom name or press `Enter` to accept the default (`agent-N`)
- `Esc` cancels without spawning
- Profile and project directory use config defaults (use `N` wizard for full control)

### Wizard Mode (Shift+N)

A 4-step interactive wizard for creating agents with custom settings:

1. **Agent Name** — custom name or leave empty for default
2. **Profile** — sandbox profile name or leave empty for default
3. **Project Directory** — path to project directory (default: current directory)
4. **Confirm** — review settings and create

Navigation: `Enter` advances, `Backspace` goes back, `Esc` cancels.

## Session Save & Restore

Press `Q` to save the current agent configuration and quit Zellij. On next launch from the same directory, agents are automatically re-spawned with the same names, profiles, project directories, and token counts.

- State is saved to `.lince-dashboard` in the directory where `zd` was launched
- Different directories maintain independent state (launch from `~/project-a` and `~/project-b` for separate sessions)
- The state file is kept after restore, so an ungraceful quit (`Ctrl-Q`) still preserves the last saved state
- If no `.lince-dashboard` file exists, the dashboard starts empty as usual

## Swimlane Grouping

When agents span multiple project directories, the dashboard automatically groups them into swimlanes with colored headers:

```
 ┌ ~/project/lince ──────────────────────────
   1  agent-1 [fullstack]  Running   1.2k/5k
 > 2  agent-2              INPUT     -
 ┌ ~/project/other-app ──────────────────────
   3  agent-3              Running   3k/12k
```

- Agents are grouped by `project_dir` and sorted by name within each group
- Swimlane headers show shortened paths (`~` replaces `$HOME`)
- When all agents share the same directory, no headers are shown (flat list)
- Group names (if set) appear as dim suffixes: `agent-1 [web-stack]`
- Navigation (`j`/`k`) moves through agents only — headers are visual-only

## Agent Detail Panel

Press `Enter` on any agent to toggle a detail panel below the table showing:

- **Status** with color coding
- **Profile** and project directory
- **Token usage** (input/output with k/M suffixes)
- **Active tool** name (reported by hooks during `PreToolUse` events)
- **Subagent count** (running sub-agents shown as `N⚙`)
- **Started at** timestamp
- **Last error** (if any)

Press `Enter` again to close the panel. `f` still focuses the agent pane.

## Agent Lifecycle

1. Press `n` (name prompt → Enter) or `N` (wizard) → dashboard spawns agent panes running `claude-sandbox run`
2. Panes are hidden by default — agents appear in the dashboard table as "Starting"
3. Claude Code hooks report status via Zellij pipe → dashboard updates to "Running"
4. When Claude needs input → status shows "INPUT" (bold yellow, attention-grabbing)
5. When sub-agents are running → status shows subagent count (e.g. "Running 2⚙")
6. Press `f` to show the agent's pane, interact, press `h` to hide it back
7. Press `Enter` to view detailed status (tokens, tool, elapsed time)
8. Press `k` to kill the agent and close its pane

## Voice Relay

VoxCode runs in the fixed bottom-left pane. When configured with `use_pipe = true` in VoxCode's `[zellij]` config, transcribed text is sent via pipe to the dashboard plugin which forwards it to the active agent:

```
VoxCode → zellij pipe --name "voxcode-text" → Dashboard Plugin → agent pane
```

To enable pipe mode in VoxCode, set in your voxcode config:

```toml
[zellij]
use_pipe = true
```

When `use_pipe = false` (default), VoxCode uses the legacy focus-switch + write-chars method, which works without the dashboard.

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

Events: `idle`, `running`, `permission`, `subagent_start`, `subagent_stop`

Additional fields in payload:
- `tool_name` — active tool name (on `PreToolUse` events)
- `subagent_type` — sub-agent type (on `SubagentStart`/`SubagentStop` events)

### File mode (fallback)

Hooks write status to `/tmp/lince-dashboard/claude-{agent_id}.state`. The plugin polls every 2 seconds.

Set `status_method = "file"` in config to use this mode.

## Architecture

```
lince-dashboard/
├── plugin/
│   ├── Cargo.toml              # Rust WASM crate
│   ├── build.sh                # Build → .wasm
│   └── src/
│       ├── main.rs             # Plugin entry, key handling, pipe dispatch
│       ├── config.rs           # TOML config parsing (dashboard settings)
│       ├── types.rs            # AgentInfo, AgentStatus, StatusMessage, WizardState, etc.
│       ├── dashboard.rs        # TUI rendering (ANSI), overlays (wizard, help)
│       ├── agent.rs            # Agent spawn/stop/tracking
│       ├── pane_manager.rs     # Pane focus/hide/show
│       └── state_file.rs       # Save/restore agent state (.lince-dashboard)
├── hooks/
│   ├── claude-status-hook.sh   # Claude Code hook → pipe + file
│   └── install-hooks.sh        # Hook installer
├── layouts/
│   ├── dashboard.kdl           # Main layout (plugin + voxcode + shell)
│   ├── dashboard-tiled.kdl     # Tiled layout (agents left, dashboard right)
│   ├── agent-single.kdl        # Reference: single floating pane
│   └── agent-multi.kdl         # Template: agent + backlog + shell tab
├── config.toml                 # Default configuration
├── install.sh                  # Interactive installer
└── README.md
```

### Plugin API usage

| Zellij API | Purpose |
|------------|---------|
| `open_command_pane_floating()` / `open_command_pane()` | Spawn agent panes (floating or tiled) |
| `hide_pane_with_id()` / `show_pane_with_id()` | Toggle pane visibility |
| `focus_terminal_pane()` | Focus a specific pane |
| `close_terminal_pane()` | Kill agent panes |
| `write_chars_to_pane_id()` | Forward voice text to agent |
| `PaneUpdate` event | Track pane lifecycle |
| `pipe()` method | Receive status + voice messages |
| `run_command()` | Detect launch directory (pwd) |
| `quit_zellij()` | Save state and exit session |

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
- Check file fallback: `cat /tmp/lince-dashboard/claude-test-1.state`
- Ensure sandbox passes env vars (see Sandbox Integration above)

### Agent panes not hiding
- This is a known Zellij behavior — `hide_pane_with_id` requires `ChangeApplicationState` permission
- The plugin requests this permission on load; accept the permission prompt

### Voice relay not working
- VoxCode must send via pipe: `zellij pipe --name "voxcode-text" --payload "text"`
- Check an agent is selected/focused in the dashboard
- Test manually: `zellij pipe --name "voxcode-text" --payload "hello"`
- Ensure VoxCode has `use_pipe = true` in its `[zellij]` config section
