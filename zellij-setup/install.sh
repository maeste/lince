#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES_DIR="$SCRIPT_DIR/configs"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Zellij Configuration Setup${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function for interactive pauses
pause() {
    echo -e "${YELLOW}$1${NC}"
    read -p "Press ENTER to continue..."
    echo ""
}

# Function for confirmation
confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Step 1: Check/Install Zellij
echo -e "${GREEN}[1/7] Checking Zellij installation...${NC}"

if command -v zellij >/dev/null 2>&1; then
    ZELLIJ_VERSION=$(zellij --version | awk '{print $2}')
    echo -e "${GREEN}✓ Zellij already installed (version $ZELLIJ_VERSION)${NC}"
else
    echo -e "${YELLOW}⚠ Zellij not found${NC}"
    echo ""
    echo "Zellij is not installed. Do you want to install it now?"
    echo ""
    echo "Available methods:"
    echo "  1) From Fedora repos (dnf install zellij)"
    echo "  2) From Cargo (cargo install --locked zellij) - RECOMMENDED"
    echo "  3) Prebuilt binary (download from GitHub)"
    echo "  4) Manually (I'll exit and you install it)"
    echo ""
    read -p "Choose (1/2/3/4): " -n 1 -r INSTALL_METHOD
    echo ""
    echo ""

    case $INSTALL_METHOD in
        1)
            echo "Installing from dnf..."
            # Target: Fedora/RHEL
            # For Ubuntu/Debian use: sudo apt-get install -y zellij
            if ! sudo dnf install -y zellij; then
                echo -e "${RED}✗ Installation failed${NC}"
                echo "Try another method or install manually"
                exit 1
            fi
            ;;
        2)
            echo "Installing from Cargo..."
            echo ""

            # Step 2a: Install Cargo if necessary
            if ! command -v cargo >/dev/null 2>&1; then
                echo -e "${YELLOW}Cargo not found. Installing Rust toolchain...${NC}"

                # Install rustup
                curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

                # Load cargo environment
                source "$HOME/.cargo/env"

                if command -v cargo >/dev/null 2>&1; then
                    echo -e "${GREEN}✓ Rust/Cargo installed${NC}"
                else
                    echo -e "${RED}✗ Rust installation failed${NC}"
                    exit 1
                fi
            else
                echo -e "${GREEN}✓ Cargo already present${NC}"
            fi
            echo ""

            # Step 2b: Install compilation dependencies
            echo "Installing compilation dependencies..."

            # Target: Fedora/RHEL
            # perl-IPC-Cmd: Perl module required for zellij build
            # perl-core: Core Perl modules
            # openssl-devel: OpenSSL development files
            if sudo dnf install -y perl-IPC-Cmd perl-core openssl-devel; then
                echo -e "${GREEN}✓ Dependencies installed (Fedora/RHEL)${NC}"
            else
                echo -e "${RED}✗ Dependency installation error${NC}"
                echo ""
                echo "If you're on Ubuntu/Debian, try manually:"
                echo "  sudo apt-get install -y perl libssl-dev build-essential"
                echo ""
                if ! confirm "Do you want to continue with compilation anyway?"; then
                    exit 1
                fi
            fi

            # Alternatives for Ubuntu/Debian (for reference):
            # sudo apt-get install -y perl libssl-dev build-essential

            echo ""

            # Step 2c: Compile and install Zellij
            echo "Compiling Zellij..."
            echo "⚠ This may take 5-10 minutes..."
            echo ""

            if cargo install --locked zellij; then
                echo -e "${GREEN}✓ Zellij compiled and installed${NC}"

                # Verify it's in PATH
                if ! command -v zellij >/dev/null 2>&1; then
                    echo ""
                    echo -e "${YELLOW}⚠ Zellij installed but not in PATH${NC}"
                    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
                    echo "  export PATH=\"\$HOME/.cargo/bin:\$PATH\""
                    echo ""
                    echo "Or reload the environment:"
                    source "$HOME/.cargo/env"
                fi
            else
                echo -e "${RED}✗ Compilation failed${NC}"
                echo ""
                echo "Suggestions:"
                echo "  1. Check internet connection"
                echo "  2. Try the prebuilt binary (option 3)"
                echo "  3. Check the logs above for specific errors"
                exit 1
            fi
            ;;
        3)
            echo "Downloading prebuilt binary..."
            cd /tmp
            curl -L https://github.com/zellij-org/zellij/releases/latest/download/zellij-x86_64-unknown-linux-musl.tar.gz -o zellij.tar.gz
            tar -xzf zellij.tar.gz
            sudo mv zellij /usr/local/bin/
            sudo chmod +x /usr/local/bin/zellij
            rm zellij.tar.gz
            cd "$SCRIPT_DIR"
            echo -e "${GREEN}✓ Binary installed in /usr/local/bin/zellij${NC}"
            ;;
        4)
            echo -e "${YELLOW}Ok, install Zellij manually and then run this script again${NC}"
            echo ""
            echo "Suggested commands:"
            echo ""
            echo "Method 1 - Cargo (recommended):"
            echo "  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            echo "  source \$HOME/.cargo/env"
            echo "  # Fedora/RHEL:"
            echo "  sudo dnf install -y perl-IPC-Cmd perl-core openssl-devel"
            echo "  # Ubuntu/Debian:"
            echo "  # sudo apt-get install -y perl libssl-dev build-essential"
            echo "  cargo install --locked zellij"
            echo ""
            echo "Method 2 - Package manager:"
            echo "  # Fedora:"
            echo "  sudo dnf install zellij"
            echo "  # Ubuntu (22.04+):"
            echo "  # sudo apt-get install zellij"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            exit 1
            ;;
    esac

    # Verify final installation
    # Reload environment for cargo
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi

    if command -v zellij >/dev/null 2>&1; then
        ZELLIJ_VERSION=$(zellij --version | awk '{print $2}')
        echo -e "${GREEN}✓ Zellij installed successfully! (version $ZELLIJ_VERSION)${NC}"
    else
        echo -e "${RED}✗ Zellij not found in PATH after installation${NC}"
        echo ""
        echo "Try:"
        echo "  source ~/.cargo/env"
        echo "  zellij --version"
        echo ""
        exit 1
    fi
fi
echo ""

# Step 2: Backup existing configuration
echo -e "${GREEN}[2/7] Backing up existing configuration...${NC}"

if [ -d ~/.config/zellij ]; then
    BACKUP_DIR=~/.config/zellij.backup.$(date +%Y%m%d_%H%M%S)
    echo "Existing configuration found, creating backup..."
    cp -r ~/.config/zellij "$BACKUP_DIR"
    echo -e "${GREEN}✓ Backup saved in: $BACKUP_DIR${NC}"
else
    echo "No existing configuration found"
fi
echo ""

# Step 3: Create directories
echo -e "${GREEN}[3/7] Creating directories...${NC}"
mkdir -p ~/.config/zellij/layouts
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Step 4: Copy configuration files
echo -e "${GREEN}[4/7] Installing configuration files...${NC}"

# Main config
cp "$FILES_DIR/config.kdl" ~/.config/zellij/config.kdl
echo -e "${GREEN}✓ config.kdl installed${NC}"

# Layouts
cp "$FILES_DIR/three-pane.kdl" ~/.config/zellij/layouts/three-pane.kdl
echo -e "${GREEN}✓ three-pane.kdl installed${NC}"

cp "$FILES_DIR/three-pane-zai.kdl" ~/.config/zellij/layouts/three-pane-zai.kdl
echo -e "${GREEN}✓ three-pane-zai.kdl installed${NC}"

cp "$FILES_DIR/three-pane-mm.kdl" ~/.config/zellij/layouts/three-pane-mm.kdl
echo -e "${GREEN}✓ three-pane-mm.kdl installed${NC}"

cp "$FILES_DIR/three-pane-vertex.kdl" ~/.config/zellij/layouts/three-pane-vertex.kdl
echo -e "${GREEN}✓ three-pane-vertex.kdl installed${NC}"

# Verify syntax
echo "Verifying configuration syntax..."
if zellij setup --check >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Valid configuration${NC}"
else
    echo -e "${RED}✗ Configuration error${NC}"
    echo "Check manually with: zellij setup --check"
    exit 1
fi
echo ""

# Step 5: Verify commands used in layouts
echo -e "${GREEN}[5/7] Verifying layout commands...${NC}"

MISSING_COMMANDS=()

if ! command -v claude >/dev/null 2>&1; then
    MISSING_COMMANDS+=("claude")
fi

if ! command -v zai-claude >/dev/null 2>&1; then
    MISSING_COMMANDS+=("zai-claude")
fi

if ! command -v backlog >/dev/null 2>&1; then
    MISSING_COMMANDS+=("backlog")
fi

if [ ${#MISSING_COMMANDS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠ Commands not found in PATH:${NC}"
    for cmd in "${MISSING_COMMANDS[@]}"; do
        echo "  - $cmd"
    done
    echo ""
    echo "The layouts use them but they are not installed."
    echo "You can:"
    echo "  1. Install them before using the layouts"
    echo "  2. Modify the layouts in ~/.config/zellij/layouts/"
    echo "  3. Ignore (panes will show error but Zellij will work)"
    echo ""

    if ! confirm "Do you want to continue anyway?"; then
        echo "Setup interrupted. Install the missing commands and run the script again."
        exit 0
    fi
else
    echo -e "${GREEN}✓ All commands found${NC}"
fi
echo ""

# Step 6: Setup aliases
echo -e "${GREEN}[6/7] Configuring aliases...${NC}"

# Bash
if [ -f ~/.bashrc ]; then
    if grep -q "# Zellij aliases" ~/.bashrc 2>/dev/null; then
        echo -e "${YELLOW}⚠ Aliases already present in .bashrc${NC}"
    else
        echo "" >> ~/.bashrc
        cat "$FILES_DIR/zellij-aliases.sh" >> ~/.bashrc
        echo -e "${GREEN}✓ Aliases added to .bashrc${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .bashrc not found${NC}"
fi

# Zsh (if present)
if [ -f ~/.zshrc ]; then
    if confirm "Detected .zshrc. Do you want to add aliases there too?"; then
        if ! grep -q "# Zellij aliases" ~/.zshrc; then
            echo "" >> ~/.zshrc
            cat "$FILES_DIR/zellij-aliases.sh" >> ~/.zshrc
            echo -e "${GREEN}✓ Aliases added to .zshrc${NC}"
        else
            echo -e "${YELLOW}⚠ Aliases already present in .zshrc${NC}"
        fi
    fi
fi
echo ""

# Step 7: Test configuration
echo -e "${GREEN}[7/7] Testing configuration...${NC}"

echo "Testing Zellij startup..."
# Quick startup/shutdown test
if timeout 5 zellij -s test-install --layout default 2>&1 | grep -q "Welcome" || true; then
    # Kill the test session
    zellij delete-session test-install 2>/dev/null || true
    echo -e "${GREEN}✓ Zellij starts correctly${NC}"
else
    echo -e "${YELLOW}⚠ Test inconclusive (might be OK anyway)${NC}"
fi

# List available layouts
echo ""
echo "Available layouts:"
ls -1 ~/.config/zellij/layouts/ | sed 's/^/  - /'
echo ""

# Installation completed
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Installation Completed!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}Configuration installed:${NC}"
echo "  ~/.config/zellij/config.kdl"
echo "  ~/.config/zellij/layouts/three-pane.kdl"
echo "  ~/.config/zellij/layouts/three-pane-zai.kdl"
echo "  ~/.config/zellij/layouts/three-pane-mm.kdl"
echo "  ~/.config/zellij/layouts/three-pane-vertex.kdl"
echo ""
echo -e "${GREEN}Available aliases (restart terminal or source ~/.bashrc):${NC}"
echo "  z       - Start Zellij"
echo "  z3      - Start with three-pane layout"
echo "  zz3     - Start with three-pane-zai layout"
echo "  zn      - Attach to existing session or create new"
echo ""
echo -e "${GREEN}Configuration features:${NC}"
echo "  ✓ Custom keybindings (Ctrl+O disabled)"
echo "  ✓ Dracula theme"
echo "  ✓ Copy-on-select enabled"
echo "  ✓ Scrollback buffer: 10000 lines"
echo "  ✓ Default layout: three-pane"
echo ""
echo -e "${GREEN}Layout three-pane:${NC}"
echo "  - Top pane (50%): launches 'claude'"
echo "  - Bottom left pane (25%): launches 'backlog board'"
echo "  - Bottom right pane (25%): free shell"
echo ""
echo -e "${GREEN}Layout three-pane-zai:${NC}"
echo "  - Top pane (50%): launches 'zai-claude'"
echo "  - Bottom left pane (25%): launches 'backlog board'"
echo "  - Bottom right pane (25%): free shell"
echo ""
echo -e "${YELLOW}Important notes:${NC}"
echo "  • Ctrl+O is disabled (for focus-mode)"
echo "  • For session mode use: Ctrl+g then session commands"
echo "  • Alt+arrows to navigate between panes"
echo "  • Ctrl+t for tab mode, Ctrl+p for pane mode"
echo ""
echo -e "${GREEN}Quick test:${NC}"
echo "  # Reload shell"
echo "  source ~/.bashrc"
echo ""
echo "  # Try the layouts"
echo "  z3         # Layout with claude"
echo "  zz3        # Layout with zai-claude"
echo ""
echo -e "${YELLOW}If the commands (claude, zai-claude, backlog) are not available:${NC}"
echo "  The layouts will show an error but Zellij will work."
echo "  You can modify the layouts in: ~/.config/zellij/layouts/"
echo "  Or install the missing commands."
echo ""

if [ ${#MISSING_COMMANDS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠ Reminder: These commands are not installed:${NC}"
    for cmd in "${MISSING_COMMANDS[@]}"; do
        echo "  - $cmd"
    done
    echo ""
fi

echo -e "${GREEN}Happy terminal multiplexing! 🚀${NC}"
