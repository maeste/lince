# LINCE Dashboard

Multi-agent TUI dashboard for managing AI coding agents in [Zellij](https://zellij.dev). A WASM plugin that lets you spawn, monitor, and switch between multiple agents — Claude Code, Codex, Gemini, OpenCode, Aider, and more — all from one terminal pane.

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

Sandboxed agents run inside the existing [agent-sandbox](../sandbox/) — the dashboard manages pane lifecycle and status, not isolation.

## Prerequisites

- **Zellij** >= 0.40 (0.43.x recommended)
- **Rust** with `wasm32-wasip1` target (`rustup target add wasm32-wasip1`)
- **At least one supported AI coding agent** (Claude Code, Codex, Gemini, OpenCode, Aider, Amp)
- **[agent-sandbox](../sandbox/)** installed and configured (for sandboxed agents)
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

# Path to agent-sandbox command
sandbox_command = "agent-sandbox"

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

## Multi-Agent Support

The dashboard supports multiple AI coding agents through a config-driven architecture. Agent types are defined in TOML configuration files with no hardcoded agent enum — adding a new agent requires zero code changes.

### How it works

Agent type definitions are loaded from two layers:

1. **`~/.agent-sandbox/agents-defaults.toml`** — shipped defaults (installed by `install.sh`)
2. **`[agents.<name>]` sections in `config.toml`** — user overrides and custom agents

User entries fully replace the default for the same key. New keys define entirely new agent types.

### Preset agent types

| Key | Display Name | Sandboxed | Native Hooks | Notes |
|-----|-------------|-----------|-------------|-------|
| `claude` | Claude Code | Yes | Yes | Default. Runs via `agent-sandbox`. Rich status via `claude-status` pipe. |
| `claude-unsandboxed` | Claude Code (unsandboxed) | **No** | Yes | Runs `claude` directly. Shows red `CLU!` in table and `[NON-SANDBOXED]` in pane title & detail panel. Supports profiles for provider selection (e.g. Vertex vs Anthropic direct). |
| `codex` | OpenAI Codex | Yes | No | Runs directly with Codex's own sandbox — no bwrap. |
| `codex-bwrap` | OpenAI Codex (bwrap) | Yes | No | Runs via `agent-sandbox`. `bwrap_conflict` handled automatically (injects `--sandbox danger-full-access`). |
| `gemini` | Google Gemini CLI | **No** | No | Runs directly without sandbox (Gemini sandbox is off by default). |
| `gemini-bwrap` | Google Gemini CLI (bwrap) | Yes | No | Runs via `agent-sandbox`. No bwrap conflict. |
| `opencode` | OpenCode | **No** | No | Runs directly without sandbox (OpenCode has no built-in sandbox). |
| `opencode-bwrap` | OpenCode (bwrap) | Yes | No | Runs via `agent-sandbox`. No bwrap conflict. |
| `aider` | Aider | Yes | No | *(sandbox preset only, not in dashboard defaults)* |
| `amp` | Amp | Yes | No | *(sandbox preset only, not in dashboard defaults)* |

### Agent type configuration fields

Each agent type is defined as a TOML table with these fields:

```toml
[agent-name]
command = ["binary", "arg1", "arg2"]   # Command template (supports {agent_id}, {project_dir}, {profile} placeholders; agent-sandbox receives --id {agent_id} which sets LINCE_AGENT_ID inside the sandbox)
pane_title_pattern = "binary"          # Pattern to match pane titles for reconciliation
status_pipe_name = "lince-status"      # Zellij pipe name for status messages
display_name = "My Agent"              # Full name shown in the UI
short_label = "AGT"                    # 3-char label for the table header
color = "green"                        # ANSI color name (blue, red, cyan, yellow, green, etc.)
sandboxed = true                       # Whether the agent runs inside bwrap sandbox
has_native_hooks = false               # If true, agent sends its own status; if false, lince-agent-wrapper is used

# Optional fields:
bwrap_conflict = false                 # Agent uses bwrap internally (nested bwrap would fail)
disable_inner_sandbox_args = []        # Args injected to disable agent's own sandbox when bwrap_conflict is true
profiles = ["__discover__"]            # Sandbox profiles for this agent type ("__discover__" = auto-discover, [] = skip profile step)
                                       # Profiles support env_unset = [...] to clean conflicting vars before setting profile env vars
home_ro_dirs = ["~/.config/myagent/"]  # Home subdirs to bind read-only in sandbox
home_rw_dirs = []                      # Home subdirs to bind read-write in sandbox
env_vars = {}                          # Environment variables to set for the agent (applied for both sandboxed and non-sandboxed agents)
event_map = {}                         # Custom mapping from agent event names to lince status strings
```

### Status reporting

Agents report their status to the dashboard through one of two mechanisms:

- **Native hooks** (`has_native_hooks = true`): The agent sends rich status events directly via its configured `status_pipe_name`. Currently only Claude Code supports this, providing tool usage, token counts, and subagent tracking.
- **`lince-agent-wrapper`** (`has_native_hooks = false`): The dashboard automatically wraps the agent command with `lince-agent-wrapper`, which sends `start` and `stopped` lifecycle events via the configured pipe. This provides basic lifecycle tracking for any agent.

### Handling bwrap conflicts

Some agents (like Codex) use bubblewrap internally. Running them inside the LINCE sandbox would create nested bwrap, which fails. There are two approaches:

- **Direct variants** (e.g. `codex`, `gemini`, `opencode`): Run the agent directly without bwrap. The agent uses its own sandbox (if any) or runs unsandboxed.
- **`-bwrap` variants** (e.g. `codex-bwrap`, `gemini-bwrap`, `opencode-bwrap`): Run via `agent-sandbox`. For agents with `bwrap_conflict = true`, the `disable_inner_sandbox_args` are automatically injected to disable the agent's own sandbox before wrapping it in bwrap.

The `-bwrap` variant handling is fully config-driven — no per-agent code branches exist.

### Unsandboxed mode

Agents with `sandboxed = false` (like `claude-unsandboxed`) run without bwrap protection. The dashboard shows:

- A red `!` suffix on the agent type label in every table row (e.g. `CLU!`)
- A red `[NON-SANDBOXED]` tag in the Zellij pane title
- A red `[NON-SANDBOXED]` warning in the detail panel

Non-sandboxed agents can use profiles to select a provider (e.g. Vertex AI vs Anthropic direct). When a profile is selected, the dashboard launches the agent via `env` — setting profile env vars and unsetting conflicting ones listed in `env_unset`. This prevents provider confusion when multiple API keys exist in the host environment.

Use this only in trusted environments where sandbox restrictions are impractical.

### Adding a custom agent

#### Automatic: `/lince-setup` skill

The easiest way to add a new agent is the `/lince-setup` skill. Run the target agent outside the dashboard and invoke the skill — the agent describes its own requirements, and the skill generates correct TOML config for both sandbox and dashboard.

```bash
# Inside your agent's CLI:
/lince-setup
```

The skill asks the agent about itself (binary, config dirs, API keys, sandbox behavior), then generates and writes the correct `[agents.<key>]` sections to both `~/.agent-sandbox/config.toml` (sandbox) and `~/.agent-sandbox/agents-defaults.toml` (dashboard). It validates the result with a dry-run. See the [Multi-Agent Guide](MULTI-AGENT-GUIDE.md) for the full flow.

The skill follows the [agentskills.io](https://agentskills.io) specification — any agent that supports the standard can use it. For agents without skill support, paste the content of `skills/lince-setup/SKILL.md` as a prompt.

#### Manual configuration

Create an `[agents.<name>]` section in `~/.config/lince-dashboard/config.toml`:

```toml
[agents.my-custom-agent]
command = ["my-agent-binary", "--auto", "--project", "{project_dir}"]
pane_title_pattern = "my-agent"
status_pipe_name = "lince-status"
display_name = "My Custom Agent"
short_label = "MCA"
color = "magenta"
sandboxed = true
has_native_hooks = false
home_ro_dirs = ["~/.config/my-agent/"]

[agents.my-custom-agent.env_vars]
MY_AGENT_API_KEY = "$MY_AGENT_API_KEY"
```

No code changes, no recompilation. The new agent type appears in the wizard (`Shift+N`) on next launch.

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

A multi-step interactive wizard for creating agents with custom settings:

1. **Agent Type** — select from available agent types (Claude Code, Codex, Gemini, etc.). Skipped if only one type is configured.
2. **Agent Name** — custom name or leave empty for default
3. **Profile** — sandbox profile name or leave empty for default
4. **Project Directory** — path to project directory (default: current directory)
5. **Confirm** — review settings and create

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
 #  Agent Name             Status
 ┌ ~/project/lince ──────────────────────────
 1  CLA  agent-1 [fullstack]  Running
 2  CDX  agent-2              INPUT
 3  CLU! quick-test           Running        ← unsandboxed
 ┌ ~/project/other-app ──────────────────────
 4  GEM  agent-3              Stopped
```

- Every row shows the **Agent** column with a 3-char type label (e.g. `CLA`, `CDX`, `GEM`) in the agent's configured color
- Unsandboxed agents show a red `!` suffix (e.g. `CLU!`) — immediately visible without opening the detail panel
- Agents are grouped by `project_dir` and sorted by name within each group
- Swimlane headers show shortened paths (`~` replaces `$HOME`)
- When all agents share the same directory, no headers are shown (flat list)
- Group names (if set) appear as dim suffixes: `agent-1 [web-stack]`
- Navigation (`j`/`k`) moves through agents only — headers are visual-only

## Agent Detail Panel

Press `Enter` on any agent to toggle a detail panel below the table showing:

- **Agent type** display name with color, plus red `[UNSANDBOXED]` warning if applicable
- **Status** with color coding
- **Profile** and project directory
- **Token usage** (input/output with k/M suffixes)
- **Active tool** name (reported by hooks during `PreToolUse` events)
- **Subagent count** (running sub-agents shown as `N⚙`)
- **Started at** timestamp
- **Last error** (if any)

Press `Enter` again to close the panel. `f` still focuses the agent pane.

## Agent Lifecycle

1. Press `n` (name prompt → Enter) or `N` (wizard) → dashboard spawns agent panes using the configured command for the selected agent type
2. Panes are hidden by default — agents appear in the dashboard table as "Starting"
3. Status hooks report via Zellij pipe → dashboard updates to "Running"
4. When an agent needs input → status shows "INPUT" (bold yellow, attention-grabbing)
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

Agents report status via `zellij pipe` using their configured `status_pipe_name`:

- **Claude Code** (`claude-status` pipe): Has native hooks that send rich status events — idle, running, permission, tool usage, subagent start/stop.
- **Codex** (`lince-status` pipe): Uses `lince-agent-wrapper` for process lifecycle and an optional Codex `notify` hook for turn-complete `idle` updates.
- **Other agents** (`lince-status` pipe): Use `lince-agent-wrapper` which sends lifecycle events — `start` and `stopped`.

```bash
# Claude Code native hook example:
zellij pipe --name "claude-status" --payload '{"agent_id":"agent-1","event":"idle"}'

# lince-agent-wrapper example (Codex, Gemini, OpenCode, etc.):
zellij pipe --name "lince-status" --payload '{"agent_id":"agent-5","event":"start"}'
```

Claude Code events: `idle`, `running`, `permission`, `subagent_start`, `subagent_stop`
Additional fields: `tool_name` (on `PreToolUse`), `subagent_type` (on `SubagentStart`/`SubagentStop`)

Codex events: `start`, `idle`, `stopped`

Wrapper events: `start`, `stopped`

### File mode (fallback)

Status files are written to `/tmp/lince-dashboard/{agent_id}.state`. The plugin polls every 2 seconds.

Set `status_method = "file"` in config to use this mode.

## Architecture

```
lince-dashboard/
├── plugin/
│   ├── Cargo.toml              # Rust WASM crate
│   ├── build.sh                # Build → .wasm
│   └── src/
│       ├── main.rs             # Plugin entry, key handling, pipe dispatch
│       ├── config.rs           # TOML config parsing, agent type loading
│       ├── types.rs            # AgentInfo, AgentStatus, StatusMessage, WizardState, etc.
│       ├── dashboard.rs        # TUI rendering (ANSI), overlays (wizard, help)
│       ├── agent.rs            # Agent spawn/stop/tracking (multi-type)
│       ├── pane_manager.rs     # Pane focus/hide/show
│       └── state_file.rs       # Save/restore agent state (.lince-dashboard)
├── hooks/
│   ├── claude-status-hook.sh   # Claude Code hook → pipe + file
│   ├── codex-status-hook.sh    # Codex notify hook → pipe + file
│   ├── lince-agent-wrapper     # Generic wrapper for agents without native hooks
│   ├── install-claude-hooks.sh # Claude installer
│   ├── install-codex-hooks.sh  # Codex installer
│   ├── update-claude-hooks.sh  # Claude updater
│   ├── update-codex-hooks.sh   # Codex updater
│   └── install-hooks.sh        # Compatibility wrapper
├── layouts/
│   ├── dashboard.kdl           # Main layout (plugin + voxcode + shell)
│   ├── dashboard-tiled.kdl     # Tiled layout (agents left, dashboard right)
│   ├── agent-single.kdl        # Reference: single floating pane
│   └── agent-multi.kdl         # Template: agent + backlog + shell tab
├── agents-defaults.toml        # Default agent type definitions
├── config.toml                 # Default dashboard configuration
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

For status reporting to work inside `agent-sandbox`, the sandbox must pass through Zellij environment variables. Add to your sandbox config (`~/.agent-sandbox/config.toml`):

```toml
[env]
passthrough = ["ZELLIJ", "ZELLIJ_SESSION_NAME", "LINCE_AGENT_ID"]
```

Agent-specific environment variables (like `OPENAI_API_KEY` for Codex or `GEMINI_API_KEY` for Gemini) are set via the `env_vars` field in the agent type configuration and are passed through automatically by the sandbox.

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
- Verify Codex notify is installed: check `~/.codex/config.toml` for the LINCE managed `notify` block
- Test Codex hook manually: `LINCE_AGENT_ID=test-1 bash ~/.local/bin/codex-status-hook.sh '{"type":"agent-turn-complete"}'`
- Check file fallback: `cat /tmp/lince-dashboard/test-1.state`
- Ensure sandbox passes env vars (see Sandbox Integration above)

### Agent panes not hiding
- This is a known Zellij behavior — `hide_pane_with_id` requires `ChangeApplicationState` permission
- The plugin requests this permission on load; accept the permission prompt

### Voice relay not working
- VoxCode must send via pipe: `zellij pipe --name "voxcode-text" --payload "text"`
- Check an agent is selected/focused in the dashboard
- Test manually: `zellij pipe --name "voxcode-text" --payload "hello"`
- Ensure VoxCode has `use_pipe = true` in its `[zellij]` config section
