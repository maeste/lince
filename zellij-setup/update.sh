#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES_DIR="$SCRIPT_DIR/configs"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Zellij Setup — Update${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Check Zellij
echo -e "${GREEN}[1/5] Checking Zellij installation...${NC}"

if ! command -v zellij >/dev/null 2>&1; then
    echo -e "${YELLOW}Zellij not found. Run install.sh first.${NC}"
    exit 1
fi

ZELLIJ_VERSION=$(zellij --version | awk '{print $2}')
echo -e "${GREEN}  OK Zellij version $ZELLIJ_VERSION${NC}"
echo ""

# Step 2: Backup existing configuration
echo -e "${GREEN}[2/5] Backing up existing configuration...${NC}"

if [ -d ~/.config/zellij ]; then
    BACKUP_DIR=~/.config/zellij.backup.$(date +%Y%m%d_%H%M%S)
    echo "Existing configuration found, creating backup..."
    cp -r ~/.config/zellij "$BACKUP_DIR"
    echo -e "${GREEN}  OK Backup saved: $BACKUP_DIR${NC}"
else
    echo "  No existing configuration found"
fi
echo ""

# Step 3: Update configuration files
echo -e "${GREEN}[3/5] Updating configuration files...${NC}"

mkdir -p ~/.config/zellij/layouts

# Main config
cp "$FILES_DIR/config.kdl" ~/.config/zellij/config.kdl
echo -e "${GREEN}  OK config.kdl updated${NC}"

# Layouts
for layout in three-pane three-pane-zai three-pane-mm three-pane-vertex; do
    cp "$FILES_DIR/${layout}.kdl" ~/.config/zellij/layouts/${layout}.kdl
    echo -e "${GREEN}  OK ${layout}.kdl updated${NC}"
done
echo ""

# Step 4: Verify syntax
echo -e "${GREEN}[4/5] Verifying configuration...${NC}"

if zellij setup --check >/dev/null 2>&1; then
    echo -e "${GREEN}  OK Valid configuration${NC}"
else
    echo -e "${YELLOW}  WARNING: Configuration has errors${NC}"
    echo "  Check manually with: zellij setup --check"
fi
echo ""

# Step 5: Update aliases
echo -e "${GREEN}[5/5] Updating aliases...${NC}"

# Check if aliases section exists, refresh it
if [ -f ~/.bashrc ]; then
    if grep -q "# Zellij aliases" ~/.bashrc 2>/dev/null; then
        # Remove old aliases block and re-add
        sed -i '/# Zellij aliases/,/^$/d' ~/.bashrc
    fi
    cat "$FILES_DIR/zellij-aliases.sh" >> ~/.bashrc
    echo -e "${GREEN}  OK Aliases updated in .bashrc${NC}"
fi

if [ -f ~/.zshrc ]; then
    if grep -q "# Zellij aliases" ~/.zshrc 2>/dev/null; then
        sed -i '/# Zellij aliases/,/^$/d' ~/.zshrc
    fi
    cat "$FILES_DIR/zellij-aliases.sh" >> ~/.zshrc
    echo -e "${GREEN}  OK Aliases updated in .zshrc${NC}"
fi
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Update Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "To use new aliases:"
echo "  source ~/.bashrc"
echo ""
echo "Available layouts:"
ls -1 ~/.config/zellij/layouts/ | sed 's/^/  - /'
echo ""
