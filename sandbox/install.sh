#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX_CMD="$SCRIPT_DIR/agent-sandbox"
INSTALL_DST="$HOME/.local/bin/agent-sandbox"
CONFIG_DIR="$HOME/.agent-sandbox"
CONFIG_DST="$CONFIG_DIR/config.toml"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   agent-sandbox — Installer${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ── Step 1: Prerequisites ──────────────────────────────────────────────
echo -e "${GREEN}[1/5] Checking prerequisites...${NC}"

OS_NAME="$(uname -s)"
HAS_BWRAP=false
HAS_NONO=false

command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Missing: python3 (3.11+)${NC}"; exit 1; }

# Check python version
PY_OK=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)" 2>/dev/null || echo 0)
if [ "$PY_OK" = "0" ]; then
    echo -e "${RED}Python 3.11+ required (for tomllib)${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ python3 $(python3 --version 2>&1 | awk '{print $2}')${NC}"

# Check sandbox backends
if command -v bwrap >/dev/null 2>&1; then
    HAS_BWRAP=true
    echo -e "${GREEN}  ✓ bwrap $(bwrap --version 2>/dev/null | awk '{print $2}')${NC}"
fi
if command -v nono >/dev/null 2>&1; then
    HAS_NONO=true
    echo -e "${GREEN}  ✓ nono $(nono --version 2>/dev/null | head -1)${NC}"
fi

# Platform-specific checks
if [ "$OS_NAME" = "Darwin" ]; then
    # macOS: bwrap is not available, nono is required
    if [ "$HAS_NONO" = false ]; then
        echo ""
        echo -e "${RED}macOS detected — agent-sandbox requires bubblewrap (Linux only).${NC}"
        echo -e "${YELLOW}On macOS, install nono as your sandbox backend:${NC}"
        echo ""
        echo "  brew install nono"
        echo ""
        echo "Then re-run this installer. See docs/nono-integration.md for details."
        echo "Project: https://github.com/always-further/nono"
        exit 1
    fi
    echo -e "${GREEN}  ✓ macOS detected — using nono as sandbox backend${NC}"
else
    # Linux: need at least one backend
    if [ "$HAS_BWRAP" = false ] && [ "$HAS_NONO" = false ]; then
        echo -e "${RED}No sandbox backend found. Install one of:${NC}"
        echo "  - bubblewrap: sudo dnf install bubblewrap  (or: sudo apt install bubblewrap)"
        echo "  - nono:       cargo install nono-cli  (or: brew install nono)"
        exit 1
    fi
fi
echo ""

# ── Step 2: Install command ────────────────────────────────────────────
echo -e "${GREEN}[2/5] Installing agent-sandbox command...${NC}"

mkdir -p "$HOME/.local/bin"
if [ -f "$INSTALL_DST" ]; then
    echo -e "${YELLOW}  Existing command found, backing up...${NC}"
    cp "$INSTALL_DST" "${INSTALL_DST}.bak.$(date +%Y%m%d_%H%M%S)"
fi
cp "$SANDBOX_CMD" "$INSTALL_DST"
chmod +x "$INSTALL_DST"
echo -e "${GREEN}  ✓ Installed: $INSTALL_DST${NC}"

# Install agents-defaults.toml in both search locations
DEFAULTS_SRC="$SCRIPT_DIR/agents-defaults.toml"
if [ -f "$DEFAULTS_SRC" ]; then
    cp "$DEFAULTS_SRC" "$HOME/.agent-sandbox/agents-defaults.toml"
    echo -e "${GREEN}  ✓ Installed: ~/.agent-sandbox/agents-defaults.toml${NC}"
    cp "$DEFAULTS_SRC" "$HOME/.local/bin/agents-defaults.toml"
    echo -e "${GREEN}  ✓ Installed: ~/.local/bin/agents-defaults.toml${NC}"
fi
echo ""

# ── Step 3: Initialize config ──────────────────────────────────────────
echo -e "${GREEN}[3/5] Setting up configuration...${NC}"

if [ -f "$CONFIG_DST" ]; then
    echo -e "${YELLOW}  Config already exists: $CONFIG_DST${NC}"
    echo "  Run 'agent-sandbox init --force' to reinitialize."
else
    "$INSTALL_DST" init
    echo -e "${GREEN}  ✓ Initialized $CONFIG_DIR${NC}"
fi

# Migration from old claude-sandbox name
if [ -f "$HOME/.local/bin/claude-sandbox" ]; then
    echo -e "${YELLOW}  Removing old claude-sandbox binary...${NC}"
    rm -f "$HOME/.local/bin/claude-sandbox"
fi
if [ -d "$HOME/.claude-sandbox" ] && [ ! -d "$HOME/.agent-sandbox" ]; then
    echo -e "${YELLOW}  Migrating ~/.claude-sandbox/ → ~/.agent-sandbox/...${NC}"
    cp -r "$HOME/.claude-sandbox" "$HOME/.agent-sandbox"
    echo -e "${GREEN}  ✓ Config migrated. You can remove ~/.claude-sandbox/ when ready.${NC}"
fi
echo ""

# ── Step 4: Verify ─────────────────────────────────────────────────────
echo -e "${GREEN}[4/5] Verifying installation...${NC}"

if "$INSTALL_DST" --help >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ agent-sandbox works${NC}"
else
    echo -e "${RED}  ✗ agent-sandbox --help failed${NC}"
    exit 1
fi
echo ""

# ── Step 5: nono integration (if available) ──────────────────────────
echo -e "${GREEN}[5/5] Checking nono integration...${NC}"

if [ "$HAS_NONO" = true ]; then
    echo -e "${GREEN}  nono detected — generating lince profiles...${NC}"
    if "$INSTALL_DST" nono-sync 2>/dev/null; then
        echo -e "${GREEN}  ✓ nono profiles generated at ~/.config/nono/profiles/lince-*.json${NC}"
    else
        echo -e "${YELLOW}  ⚠ nono-sync failed (config may not be initialized yet).${NC}"
        echo -e "${YELLOW}    Run 'agent-sandbox nono-sync' after 'agent-sandbox init'.${NC}"
    fi
    if [ "$OS_NAME" = "Darwin" ] || [ "$HAS_BWRAP" = false ]; then
        echo -e "${GREEN}  Backend set to nono (bwrap not available)${NC}"
    else
        echo -e "${GREEN}  Backend set to auto (prefers agent-sandbox, falls back to nono)${NC}"
    fi
else
    echo -e "${YELLOW}  nono not installed — using agent-sandbox (bwrap) backend${NC}"
    if [ "$OS_NAME" = "Darwin" ]; then
        echo -e "${YELLOW}  Install nono for macOS support: brew install nono${NC}"
    fi
fi
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Installation Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Command:  $INSTALL_DST"
echo "Config:   $CONFIG_DST"
if [ "$HAS_NONO" = true ]; then
    echo "Backend:  $([ "$OS_NAME" = "Darwin" ] || [ "$HAS_BWRAP" = false ] && echo "nono" || echo "auto (agent-sandbox + nono)")"
else
    echo "Backend:  agent-sandbox (bwrap)"
fi
echo ""
echo "Usage:"
echo "  agent-sandbox run              # run with defaults"
echo "  agent-sandbox run -P vertex    # run with a profile"
echo "  agent-sandbox status           # show sandbox status"
if [ "$HAS_NONO" = true ]; then
    echo "  agent-sandbox nono-sync        # regenerate nono profiles"
fi
echo ""
echo "Edit $CONFIG_DST to configure profiles, API keys, and env passthrough."
echo ""
