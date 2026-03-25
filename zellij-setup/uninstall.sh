#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Zellij Setup — Uninstaller${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Step 1: Remove configuration
echo -e "${GREEN}[1/4] Removing Zellij configuration...${NC}"

if [ -d ~/.config/zellij ]; then
    echo -e "${YELLOW}Found: ~/.config/zellij${NC}"
    if confirm "  Remove Zellij configuration directory?"; then
        BACKUP_DIR=~/.config/zellij.uninstall.$(date +%Y%m%d_%H%M%S)
        mv ~/.config/zellij "$BACKUP_DIR"
        echo -e "${GREEN}  OK Moved to: $BACKUP_DIR${NC}"
    fi
else
    echo "  No configuration directory found"
fi
echo ""

# Step 2: Remove aliases
echo -e "${GREEN}[2/4] Removing shell aliases...${NC}"

for rc in ~/.bashrc ~/.zshrc; do
    if [ -f "$rc" ]; then
        if grep -q "# Zellij aliases" "$rc" 2>/dev/null; then
            echo -e "${YELLOW}Found aliases in $(basename $rc)${NC}"
            if confirm "  Remove aliases from $(basename $rc)?"; then
                sed -i '/# Zellij aliases/,/^$/d' "$rc"
                echo -e "${GREEN}  OK Removed from $(basename $rc)${NC}"
            fi
        else
            echo "  No aliases found in $(basename $rc)"
        fi
    fi
done
echo ""

# Step 3: Remove Zellij (optional)
echo -e "${GREEN}[3/4] Zellij removal...${NC}"

if command -v zellij >/dev/null 2>&1; then
    if confirm "  Remove Zellij binary?"; then
        ZELLIJ_PATH=$(command -v zellij)
        if [[ "$ZELLIJ_PATH" == "$HOME/.cargo/bin/"* ]]; then
            cargo uninstall zellij 2>/dev/null && echo -e "${GREEN}  OK Removed via cargo${NC}" || true
        elif [[ "$ZELLIJ_PATH" == "/usr/local/bin/"* ]]; then
            sudo rm "$ZELLIJ_PATH" && echo -e "${GREEN}  OK Removed from /usr/local/bin/${NC}" || true
        else
            echo -e "${YELLOW}  WARNING: Zellij installed in non-standard location: $ZELLIJ_PATH${NC}"
            echo "  Remove manually if needed"
        fi
    fi
else
    echo "  Zellij not found in PATH"
fi
echo ""

# Step 4: Verify cleanup
echo -e "${GREEN}[4/4] Verifying cleanup...${NC}"

if [ -d ~/.config/zellij ]; then
    echo -e "${YELLOW}  WARNING: ~/.config/zellij still exists${NC}"
else
    echo -e "${GREEN}  OK Configuration removed${NC}"
fi

ALIASES_REMAIN=0
for rc in ~/.bashrc ~/.zshrc; do
    if [ -f "$rc" ] && grep -q "# Zellij aliases" "$rc" 2>/dev/null; then
        ALIASES_REMAIN=1
    fi
done

if [ "$ALIASES_REMAIN" -eq 1 ]; then
    echo -e "${YELLOW}  WARNING: Some aliases may still remain${NC}"
else
    echo -e "${GREEN}  OK Aliases removed${NC}"
fi
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Uninstall Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Source files in zellij-setup/ were NOT removed."
echo "To reinstall later: cd zellij-setup && ./install.sh"
echo ""
