#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DST="$HOME/.local/bin/lince-lab"
SHARE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lince/lince-lab"
SKILL_DST="$HOME/.claude/skills/lince-lab"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lince-lab"

removed_any=false

echo "Uninstalling lince-lab..."

# CLI + any timestamped backups.
if [ -f "$INSTALL_DST" ]; then
    rm -f "$INSTALL_DST"
    echo -e "${GREEN}  ✓ Removed $INSTALL_DST${NC}"
    removed_any=true
fi
for bak in "${INSTALL_DST}.bak."*; do
    [ -e "$bak" ] || continue
    rm -f "$bak"
    echo -e "${GREEN}  ✓ Removed $bak${NC}"
    removed_any=true
done

# Installed package + recipes + templates (the whole share dir).
if [ -d "$SHARE_DIR" ]; then
    rm -rf "$SHARE_DIR"
    echo -e "${GREEN}  ✓ Removed $SHARE_DIR${NC}"
    removed_any=true
fi

# Skill.
if [ -d "$SKILL_DST" ]; then
    rm -rf "$SKILL_DST"
    echo -e "${GREEN}  ✓ Removed $SKILL_DST${NC}"
    removed_any=true
fi

# Config is left in place by default (user data); report where it lives.
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}  Config left in place: $CONFIG_DIR${NC}"
    echo -e "${YELLOW}    Remove it manually if you no longer want it: rm -rf \"$CONFIG_DIR\"${NC}"
fi

if [ "$removed_any" = false ]; then
    echo "lince-lab is not installed."
else
    echo -e "${GREEN}Done.${NC}"
fi
