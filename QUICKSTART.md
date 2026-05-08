# LINCE Quickstart Guide

Get up and running with LINCE in minutes. This guide walks you through the installation process.

## What is LINCE?

LINCE (Linux Intelligent Native Coding Environment) is a toolkit that turns your terminal into a multi-agent engineering workstation. Core modules:

| Module | Purpose |
|--------|---------|
| **agent-sandbox** | Secure sandbox for running AI coding agents |
| **lince-dashboard** | TUI dashboard to manage multiple AI agents |

Optional voice input is available via [VoxCode](https://github.com/RisorseArtificiali/voxcode) (separate project).

---

## Quick Install (Interactive)

```bash
cd /path/to/lince
./quickstart.sh
```

The installer will check prerequisites, install sandbox + dashboard, and show usage instructions.

For non-interactive install:
```bash
./quickstart.sh --mini --yes
```

---

## Manual Install (Step by Step)

### Step 1: Install agent-sandbox

```bash
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
- Offers to install optimized Zellij keybindings (Ctrl+O disabled for agent compatibility)
- Creates shell aliases: `lince`, `lince-floating`, `zd` (legacy), `z`, `zn`

Verification:
```bash
source ~/.bashrc
lince    # launch the dashboard
```

---

## Usage

### Launch the Dashboard

```bash
source ~/.bashrc
lince
```

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

---

## Optional: Voice Input

For voice-controlled coding, install [VoxCode](https://github.com/RisorseArtificiali/voxcode) separately. Once installed, the dashboard can use it automatically (re-run `lince-dashboard/install.sh` to enable the VoxCode layout).

---

## Uninstall

```bash
cd sandbox && ./uninstall.sh
cd lince-dashboard && ./uninstall.sh
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

### Dashboard won't start

1. Check Zellij version (need >= 0.40):
   ```bash
   zellij --version
   ```

2. Check plugin exists:
   ```bash
   ls ~/.config/zellij/plugins/lince-dashboard.wasm
   ```

3. Check aliases:
   ```bash
   alias lince
   ```

### Ctrl+Shift+C kills agent (Terminator + Zellij)

When running agents inside the LINCE Dashboard (Zellij) on **Terminator**, pressing **Ctrl+Shift+C** to copy also delivers a SIGINT to the agent in the focused pane, interrupting it. The same key combo works fine in Terminator without Zellij — the issue only appears with the Terminator + Zellij combination.

**Fix**: remap Terminator's copy shortcut to a key that doesn't include Ctrl+C.

Option 1 — Edit `~/.config/terminator/config`:
```ini
[keybindings]
copy = <Primary>Insert
```
Then restart Terminator. Ctrl+Insert now copies without sending SIGINT.

Option 2 — Via GUI: open **Terminator → Preferences → Keybindings**, find **copy_clipboard**, and bind it to `Ctrl+Insert` or another key that doesn't include Ctrl+C.

---

## Requirements Summary

| Component | Required For | Notes |
|-----------|--------------|-------|
| Linux | All | Tested on Fedora 43, Ubuntu |
| macOS | Experimental | Via nono sandbox backend |
| Zellij >= 0.40 | Dashboard | Terminal multiplexer |
| Rust + wasm32-wasip1 | Dashboard | For building plugin |
| Claude Code | Sandbox | AI coding agent |
| bubblewrap | Sandbox (Linux) | Isolation technology |
| nono | Sandbox (macOS) | Alternative sandbox backend |
| Python 3.11+ | Sandbox | Runtime |

---

## Quick Reference

```bash
# Install
./quickstart.sh --mini --yes

# Update
cd sandbox && ./update.sh
cd lince-dashboard && ./update.sh

# Launch
lince
```
