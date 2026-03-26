# LINCE Quickstart Guide

Get up and running with LINCE in minutes. This guide walks you through the installation process based on your needs.

## What is LINCE?

LINCE (Linux Intelligent Native Coding Environment) is a toolkit that turns your Linux terminal into a multi-agent engineering workstation. It includes:

| Module | Purpose |
|--------|---------|
| **agent-sandbox** | Secure sandbox for running AI coding agents |
| **lince-dashboard** | TUI dashboard to manage multiple AI agents |
| **voxcode** | Voice input (speak to your AI agents) |
| **voxtts** | Text-to-speech output (AI reads back to you) |
| **zellij-setup** | Terminal multiplexer configuration |

## Choose Your Setup

### Option A: Mini Setup (~15 minutes)

**Best for**: Try out the dashboard with sandboxed Claude Code.

```
Components: sandbox + lince-dashboard
What you get: Multi-agent dashboard with secure Claude Code execution
What you skip: Voice input/output, Zellij aliases
```

### Option B: Full Setup (~30 minutes)

**Best for**: Complete voice-controlled AI coding workstation.

```
Components: sandbox + lince-dashboard + voxcode + voxtts + zellij-setup
What you get: Everything — voice input, TTS output, all aliases/layouts
What you skip: Nothing
```

### Option C: Custom Setup

**Best for**: Advanced users who know exactly what they need.

Choose which modules to install individually.

---

## Quick Install (Interactive)

The easiest way to install is to use the central installer:

```bash
cd /path/to/lince
./quickstart.sh
```

This will show an interactive menu:
```
================================================
   LINCE Quickstart Installer
================================================

Select your setup:

  1) Mini     (sandbox + dashboard)
  2) Full     (all modules)
  3) Custom   (choose modules)
  4) Exit

Choice: _
```

Follow the prompts. The installer will:
1. Check prerequisites
2. Install selected modules
3. Verify everything works
4. Show usage instructions

---

## Manual Install (Step by Step)

If you prefer to install modules individually:

### Step 1: Install agent-sandbox (Required for dashboard)

```bash
cd lince
cd sandbox
./install.sh
```

What it does:
- Copies `agent-sandbox` to `~/.local/bin/`
- Creates `~/.agent-sandbox/` config directory
- Runs `agent-sandbox init` to set up environment
- Installs default agent configurations

Verification:
```bash
agent-sandbox --help
```

### Step 2: Install lince-dashboard

```bash
cd lince-dashboard
./install.sh
```

What it does:
- Builds the WASM plugin (~900 KB)
- Installs plugin to `~/.config/zellij/plugins/`
- Installs layouts to `~/.config/zellij/layouts/`
- Installs Claude Code status hooks
- Creates `zd` shell alias

Verification:
```bash
source ~/.bashrc
zd --help   # or just: zd
```

### Step 3: Install Zellij setup (Optional, for aliases/layouts)

```bash
cd zellij-setup
./install.sh
```

What it does:
- Installs Zellij config (`~/.config/zellij/config.kdl`)
- Installs layouts (three-pane variants)
- Adds aliases: `z`, `z3`, `zz3`, `zn`

### Step 4: Install VoxCode (Optional, for voice input)

```bash
cd voxcode
./install.sh
```

What it does:
- Installs `voxcode` command via uv
- Creates config at `~/.config/voxcode/config.toml`
- Checks audio devices

Verification:
```bash
voxcode --list-devices
```

### Step 5: Install VoxTTS (Optional, for TTS output)

```bash
cd voxtts
./install.sh
```

What it does:
- Installs `voxtts` command via uv
- Creates config at `~/.config/voxtts/config.toml`
- Checks audio output devices

Verification:
```bash
voxtts --list-devices
```

---

## Usage

### Launch the Dashboard

```bash
source ~/.bashrc
zd
```

This opens the LINCE dashboard in Zellij with:
- The dashboard plugin on the right
- VoxCode (voice input) bottom-left
- Shell bottom-right

### Dashboard Controls

| Key | Action |
|-----|--------|
| `n` | Spawn new agent (quick name prompt) |
| `N` | Spawn new agent (wizard with full options) |
| `r` | Rename selected agent |
| `x` | Kill selected agent |
| `f` | Focus (show) agent pane |
| `h` | Hide focused agent pane |
| `j` / `Down` | Select next agent |
| `k` / `Up` | Select previous agent |
| `Q` | Save state and quit |
| `?` | Show help overlay |

### Voice Commands (with VoxCode)

Say these to control VoxCode:

| Say this | Action |
|----------|--------|
| "comando: invia" | Send buffer to AI agent |
| "comando: cancella" | Clear buffer |
| "comando: pausa" | Pause listening |
| "comando: riprendi" | Resume listening |

### Text-to-Speech (with VoxTTS)

```bash
# Read a file aloud
voxtts notes.md --play

# Read clipboard
voxtts --clipboard --play

# Save to MP3
voxtts article.txt -o article.mp3

# Read current pane
voxtts --pane --play
```

---

## Uninstall

Each module can be uninstalled individually:

```bash
# Sandbox
cd sandbox && ./uninstall.sh

# Dashboard
cd lince-dashboard && ./uninstall.sh

# Zellij setup
cd zellij-setup && ./uninstall.sh

# VoxCode
cd voxcode && ./uninstall.sh

# VoxTTS
cd voxtts && ./uninstall.sh
```

---

## Troubleshooting

### "command not found" errors

Make sure your shell config is sourced:
```bash
source ~/.bashrc
```

If you added tools to `~/.local/bin/`, ensure it's in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Voice not working

1. Check microphone:
   ```bash
   voxcode --list-devices
   ```

2. Try push-to-talk mode:
   ```bash
   voxcode --mode ptt
   ```

### Dashboard won't start

1. Check Zellij version:
   ```bash
   zellij --version
   ```
   You need version >= 0.40

2. Check plugin exists:
   ```bash
   ls ~/.config/zellij/plugins/
   ```

3. Check aliases:
   ```bash
   alias zd
   ```

### Audio playback issues

List available devices:
```bash
voxtts --list-devices
```

Set specific device in config:
```toml
[audio]
device = 0  # or another number
```

---

## Next Steps

- Read the full [README.md](../README.md) for complete documentation
- Explore individual module READMEs in each directory
- Configure profiles in `~/.agent-sandbox/config.toml`
- Add custom agent types to the dashboard

---

## Requirements Summary

| Component | Required For | Notes |
|-----------|--------------|-------|
| Linux | All | Tested on Fedora 43 |
| Zellij >= 0.40 | Dashboard | Terminal multiplexer |
| Rust + wasm32-wasip1 | Dashboard | For building plugin |
| Claude Code | Sandbox | AI coding agent |
| bubblewrap | Sandbox | Isolation technology |
| Python 3.11+ | Sandbox, VoxCode | Runtime |
| uv | VoxCode, VoxTTS | Package manager |
| NVIDIA GPU | VoxCode, VoxTTS | Optional, for faster inference |
| Microphone | VoxCode | For voice input |
| Speakers | VoxTTS | For audio output |

---

## Quick Reference

```bash
# One-liner: Full install
./quickstart.sh --full --yes

# One-liner: Mini install
./quickstart.sh --mini --yes

# Update all modules
cd sandbox && ./update.sh
cd lince-dashboard && ./update.sh
cd voxcode && ./update.sh
cd voxtts && ./update.sh
cd zellij-setup && ./update.sh
```
