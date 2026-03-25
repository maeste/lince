# LINCE

**Linux Intelligent Native Coding Environment**

A toolkit that turns your Linux terminal into a multi-agent engineering workstation — spawn parallel Claude Code agents, track their status in real time, relay voice commands, all from a single TUI dashboard running in Zellij.

## Demo

![LINCE demo](demo.gif)

> The full workflow: voice command → Whisper transcription → Claude Code executes in sandbox → backlog updates — all from one terminal.

## The Dashboard

The primary way to use LINCE is the **TUI Dashboard** — a Zellij WASM plugin that acts as a command center for multiple Claude Code agents.

```
┌─────────────────────────────────────────────────────────┐
│  LINCE Dashboard                                        │
│ ┌───┬────────────┬──────────┬────────┬────────┬───────┐ │
│ │ # │ Name       │ Status   │ Tokens │Profile │Project│ │
│ ├───┼────────────┼──────────┼────────┼────────┼───────┤ │
│ │ 1 │ backend    │ Running  │ 1.2k/5k│ vertex │ api/  │ │
│ │>2 │ frontend   │ INPUT    │    -   │        │ web/  │ │
│ │ 3 │ tester     │ Idle     │ 3k/12k │ zai    │ tests/│ │
│ └───┴────────────┴──────────┴────────┴────────┴───────┘ │
├───────────────────────┬─────────────────────────────────┤
│                       │                                 │
│   VoxCode             │   Shell                         │
│   Voice input →       │                                 │
│   relayed to agents   │                                 │
│                       │                                 │
└───────────────────────┴─────────────────────────────────┘
```

What the dashboard gives you:

- **Multi-agent**: Spawn up to 8 AI coding agents in parallel (Claude Code, Codex, Gemini, OpenCode, Aider, and any custom agent), each in its own sandboxed pane
- **Real-time status**: See at a glance which agents are running, waiting for input, or idle — color-coded with token usage
- **Pane control**: Show/hide agent panes with a keystroke (`f` to focus, `h` to hide)
- **Voice relay**: VoxCode transcriptions are piped directly to the focused agent
- **Session persistence**: Save/restore your agent constellation across sessions (`Q` to save & quit)
- **Swimlane grouping**: Agents auto-grouped by project directory when working across repos
- **Sandbox isolation**: Every agent runs inside [agent-sandbox](sandbox/) — full autonomy, zero host risk

## Quick Start

For a detailed step-by-step guide with scenarios (Mini/Full/Custom), troubleshooting, and quick reference, see [QUICKSTART.md](QUICKSTART.md).

### Prerequisites

- **Linux** (tested on Fedora 43, works on Ubuntu/Debian/Arch)
- **Zellij** >= 0.40
- **Claude Code** (`npm install -g @anthropic-ai/claude-code`)
- **bubblewrap** (`sudo dnf install bubblewrap` / `sudo apt install bubblewrap`)
- **Rust** with `wasm32-wasip1` target (for building the dashboard plugin)
- **A microphone** and an **NVIDIA GPU** (for VoxCode/VoxTTS; CPU-only works but is slower)
- **[uv](https://github.com/astral-sh/uv)** (for VoxCode and VoxTTS Python environments)

### Step 1: Install the sandbox

```bash
cd sandbox
./install.sh
```

This creates an isolated environment where Claude has full write access to your project but physically cannot reach your SSH keys, cloud credentials, or anything outside the project directory. See [sandbox/README.md](sandbox/README.md) for the full configuration reference.

### Step 2: Install the dashboard

```bash
cd lince-dashboard
./install.sh
```

The installer builds the WASM plugin, copies it to `~/.config/zellij/plugins/`, installs Zellij layouts, sets up Claude Code status hooks, and creates the `zd` shell alias. After sourcing your shell config:

```bash
source ~/.bashrc
zd    # launch the dashboard
```

### Step 3: Set up VoxCode (optional, for voice control)

```bash
cd voxcode
./install.sh
```

Or use `uv sync` if you prefer running from source:
```bash
cd voxcode
uv sync
uv run voxcode --list-devices    # find your microphone
uv run voxcode --audio-device <number>  # test transcription
```

The dashboard layout starts VoxCode in the bottom-left pane. Transcriptions are piped directly to the focused agent — no manual pane switching needed. See [voxcode/README.md](voxcode/README.md) for details.

### Step 4: Launch

```bash
zd
```

Press `n` to spawn an agent (quick), or `N` for the full wizard (name, sandbox profile, project directory). Press `?` for the full keybindings overlay.

### Alternative: Use the Quickstart Installer

For an interactive installer that handles all modules with dependency resolution:
```bash
./quickstart.sh
```

See [QUICKSTART.md](QUICKSTART.md) for more options (--mini, --full, --yes flags).

### The Workflow in Practice

```
You (speaking):  "Pick up the next task from the backlog and start working on it"
                        │
                        ▼
VoxCode:         Whisper transcribes locally → pipes text to dashboard
                        │
                        ▼
Dashboard:       Routes text to focused/selected agent
                        │
                        ▼
Claude Code:     Reads the backlog via MCP → picks a task →
                 marks it in-progress → writes code → runs tests
                        │
                        ▼
Dashboard:       Status updates in real-time (Running → INPUT → Idle)
                 Token usage tracked, tool names shown in detail panel
```

## Modules

### [lince-dashboard/](lince-dashboard/)

The multi-agent TUI dashboard — a Zellij WASM plugin (Rust, ~900 KB) that manages multiple AI coding agents (Claude Code, Codex, Gemini, OpenCode, and any custom agent). Spawn agents, monitor status, show/hide panes, relay voice input, persist sessions. Agent types are fully config-driven — add new agents via TOML or use the `/lince-setup` skill. See [lince-dashboard/README.md](lince-dashboard/README.md).

### [sandbox/](sandbox/)

Bubblewrap-based sandbox for running AI coding agents safely. Restricts filesystem access, blocks git push, isolates environment variables, and hides host processes — with near-zero overhead. Supports any agent via `--agent` flag (`agent-sandbox run -a codex`, `-a gemini`, etc.). Used by the dashboard to spawn every agent.

### [voxcode/](voxcode/)

Voice-controlled coding assistant that bridges local speech recognition (Whisper, runs on your GPU) with Claude Code. In dashboard mode, transcriptions are piped directly to agents. All audio processing happens locally — nothing leaves your machine.

### [voxtts/](voxtts/)

Text-to-Speech with local GPU/CPU engines. The output counterpart to VoxCode — converts text files, clipboard content, stdin pipes, or terminal pane captures into natural-sounding audio. Supports Kokoro TTS (neural, high quality) and Piper TTS (fast, CPU-optimized), with auto language detection, streaming playback, and MP3/WAV output. All synthesis runs locally.

```bash
voxtts --pane --play           # read pane content through speakers
voxtts notes.md -o notes.mp3  # convert markdown to audio file
```

### `/lince-setup` skill (bundled with lince-dashboard)

An [agentskills.io](https://agentskills.io)-compliant skill that lets any AI coding agent register itself with the lince ecosystem. The agent knows its own requirements (binary, config dirs, API keys, sandbox behavior); the skill knows the lince config format. Together they generate correct TOML configuration for both agent-sandbox and lince-dashboard — no manual config writing needed.

Run the target agent outside the dashboard and invoke `/lince-setup`. The agent introspects itself, the skill generates config, and the new agent type appears in the dashboard wizard on next launch. Works with any agent that supports the agentskills.io standard; for others, paste `SKILL.md` as a prompt.

Installed automatically by `lince-dashboard/install.sh` to `~/.claude/skills/lince-setup/`.

### [agent-ready-skill/](agent-ready-skill/)

[Agent Skills](https://agentskills.io) that assess a project's readiness for agentic coding. Scans 8 dimensions (instructions, navigability, testing, CI/CD, specs, skills, docs, Claude-specific tooling), produces a 0-100 score, and can auto-generate missing files to improve readiness. Works with Claude Code via symlinks into `.claude/skills/`.

### [zellij-setup/](zellij-setup/)

Custom [Zellij](https://zellij.dev) configuration with predefined layouts, keybindings, Dracula theme, and shell aliases. Multiple layouts support different provider profiles (Vertex AI, direct API, etc.).

## Alternative: Single-Agent Setup

If you prefer a simpler setup without the dashboard — one Claude Code agent, one task board, one voice pane — you can use the individual modules directly with Zellij:

```bash
# Install sandbox + zellij-setup + voxcode separately
cd sandbox && ./install.sh
cd ../zellij-setup && ./install.sh
cd ../voxcode && uv sync

source ~/.bashrc
z3    # three-pane layout: Claude Code + Backlog.md + VoxCode
```

| Alias | Layout |
|-------|--------|
| `z3` | Three-pane with default provider profile |
| `zz3` | Three-pane with Z.ai (Vertex AI) profile |

This gives you the original LINCE workflow:
1. **Top pane**: Claude Code in sandbox
2. **Bottom-left**: [Backlog.md](https://github.com/backlog-md/backlog) task board
3. **Bottom-right**: VoxCode voice input

See [zellij-setup/README.md](zellij-setup/README.md) for layout details and customization.

## Backlog.md Integration

Both the dashboard and single-agent setups work with [Backlog.md](https://github.com/backlog-md/backlog) — a markdown-native task manager that lives in your repo and integrates with Claude via MCP. Install it following the [Backlog.md documentation](https://github.com/backlog-md/backlog). When Claude has the Backlog.md MCP server configured, it can create tasks, update progress, and check what's next — all from within the sandboxed session.

## License

MIT
