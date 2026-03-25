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
echo -e "${GREEN}[1/4] Checking prerequisites...${NC}"

MISSING=()
command -v python3 >/dev/null 2>&1 || MISSING+=("python3 (3.11+)")
command -v bwrap >/dev/null 2>&1 || MISSING+=("bubblewrap (bwrap)")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${RED}Missing:${NC}"
    for m in "${MISSING[@]}"; do echo "  - $m"; done
    echo ""
    echo "Install with: sudo dnf install bubblewrap  (or: sudo apt install bubblewrap)"
    exit 1
fi

# Check python version
PY_OK=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)" 2>/dev/null || echo 0)
if [ "$PY_OK" = "0" ]; then
    echo -e "${RED}Python 3.11+ required (for tomllib)${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ python3 $(python3 --version 2>&1 | awk '{print $2}')${NC}"
echo -e "${GREEN}  ✓ bwrap $(bwrap --version 2>/dev/null | awk '{print $2}')${NC}"
echo ""

# ── Step 2: Install command ────────────────────────────────────────────
echo -e "${GREEN}[2/4] Installing agent-sandbox command...${NC}"

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
echo -e "${GREEN}[3/4] Setting up configuration...${NC}"

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
echo -e "${GREEN}[4/4] Verifying installation...${NC}"

if "$INSTALL_DST" --help >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ agent-sandbox works${NC}"
else
    echo -e "${RED}  ✗ agent-sandbox --help failed${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Installation Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Command:  $INSTALL_DST"
echo "Config:   $CONFIG_DST"
echo ""
echo "Usage:"
echo "  agent-sandbox run              # run with defaults"
echo "  agent-sandbox run -P vertex    # run with a profile"
echo "  agent-sandbox status           # show sandbox status"
echo ""
echo "Edit $CONFIG_DST to configure profiles, API keys, and env passthrough."
echo ""
