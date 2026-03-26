#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/voxtts"
CONFIG_DST="$CONFIG_DIR/config.toml"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   VoxTTS — Installer${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Prerequisites
echo -e "${GREEN}[1/4] Checking prerequisites...${NC}"

if ! command -v uv >/dev/null 2>&1; then
    echo -e "${RED}Error: uv is required but not installed.${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo -e "${GREEN}  OK uv $(uv --version 2>/dev/null | awk '{print $2}')${NC}"

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}Error: python3 is required.${NC}"
    exit 1
fi
PY_OK=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)" 2>/dev/null || echo 0)
if [ "$PY_OK" = "0" ]; then
    echo -e "${RED}Error: Python 3.11+ required${NC}"
    exit 1
fi
echo -e "${GREEN}  OK python3 $(python3 --version 2>&1 | awk '{print $2}')${NC}"
echo ""

# Step 2: Install as global tool
echo -e "${GREEN}[2/4] Installing voxtts as system command...${NC}"

uv tool install --from "$SCRIPT_DIR" --force --reinstall voxtts 2>&1 | while read -r line; do
    echo "  $line"
done

if command -v voxtts >/dev/null 2>&1; then
    echo -e "${GREEN}  OK voxtts installed at $(command -v voxtts)${NC}"
else
    if [ -f "$HOME/.local/bin/voxtts" ]; then
        echo -e "${YELLOW}  WARNING: Installed at ~/.local/bin/voxtts but not in PATH${NC}"
        echo "  Add to your shell config: export PATH=\"\$HOME/.local/bin:\$PATH\""
    else
        echo -e "${RED}  ERROR: Installation failed${NC}"
        exit 1
    fi
fi
echo ""

# Step 3: Install config
echo -e "${GREEN}[3/4] Setting up configuration...${NC}"

mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_DST" ]; then
    echo -e "${YELLOW}  Config already exists — keeping current: $CONFIG_DST${NC}"
else
    cp "$SCRIPT_DIR/config.example.toml" "$CONFIG_DST"
    echo -e "${GREEN}  OK Installed: $CONFIG_DST${NC}"
    echo -e "${YELLOW}  Edit this file to set your audio device and preferences.${NC}"
fi
echo ""

# Step 4: Check audio device
echo -e "${GREEN}[4/4] Audio device check...${NC}"

echo "  Available audio output devices:"
voxtts --list-devices 2>/dev/null | while read -r line; do
    echo "    $line"
done || echo -e "${YELLOW}  Could not list devices (audio driver needed)${NC}"
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Installation Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Command:  $(command -v voxtts 2>/dev/null || echo '~/.local/bin/voxtts')"
echo "Config:   $CONFIG_DST"
echo ""
echo "Usage:"
echo "  voxtts file.txt --play              # read file aloud"
echo "  voxtts --clipboard --play           # read clipboard"
echo "  voxtts notes.md -o notes.mp3         # save to MP3"
echo ""
echo "Edit $CONFIG_DST to set defaults."
echo ""
