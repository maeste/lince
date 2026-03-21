#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DST="$HOME/.local/bin/claude-sandbox"
CONFIG_DIR="$HOME/.claude-sandbox"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   claude-sandbox — Uninstaller${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ── Command ────────────────────────────────────────────────────────────
if [ -f "$INSTALL_DST" ]; then
    echo -e "${YELLOW}Found: $INSTALL_DST${NC}"
    if confirm "  Remove command?"; then
        rm -f "$INSTALL_DST" "${INSTALL_DST}.bak."*
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Command not found — skipping"
fi
echo ""

# ── Config directory ───────────────────────────────────────────────────
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}Found: $CONFIG_DIR${NC}"
    echo -e "${RED}  WARNING: This contains your config, claude config copy, and logs.${NC}"
    if confirm "  Remove entire config directory?"; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Config directory not found — skipping"
fi
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Uninstall Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Source files in sandbox/ were NOT removed."
echo "To reinstall later: cd sandbox && ./install.sh"
echo ""
