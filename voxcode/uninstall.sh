#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONFIG_DIR="$HOME/.config/voxcode"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   VoxCode — Uninstaller${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ── Command ────────────────────────────────────────────────────────────
if command -v uv >/dev/null 2>&1; then
    if uv tool list 2>/dev/null | grep -q voxcode; then
        echo -e "${YELLOW}Found voxcode in uv tools${NC}"
        if confirm "  Remove voxcode command?"; then
            uv tool uninstall voxcode
            echo -e "${GREEN}  ✓ Removed${NC}"
        fi
    else
        echo "  voxcode not in uv tools — skipping"
    fi
else
    echo "  uv not found — skipping command removal"
fi
echo ""

# ── Config ─────────────────────────────────────────────────────────────
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}Found: $CONFIG_DIR${NC}"
    if confirm "  Remove config directory?"; then
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
echo "Source files in voxcode/ were NOT removed."
echo "To reinstall later: cd voxcode && ./install.sh"
echo ""
