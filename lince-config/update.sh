#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DST="$HOME/.local/bin/lince-config"

echo "Updating lince-config..."

# Prerequisites — same checks as install.sh, so a Python downgrade or a missing
# tomlkit doesn't leave a broken install.
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Missing: python3 (3.11+)${NC}"; exit 1; }

PY_OK=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)" 2>/dev/null || echo 0)
if [ "$PY_OK" = "0" ]; then
    echo -e "${RED}Python 3.11+ required (for tomllib)${NC}"
    exit 1
fi

python3 -c "import tomlkit" 2>/dev/null || {
    echo -e "${YELLOW}tomlkit not found. Installing...${NC}"
    pip install --user tomlkit 2>/dev/null || \
        pip install --user --break-system-packages tomlkit 2>/dev/null || {
        echo -e "${RED}Failed to install tomlkit. Install manually: pip install tomlkit${NC}"
        exit 1
    }
}

cp "$SCRIPT_DIR/lince-config" "$INSTALL_DST"
chmod +x "$INSTALL_DST"
echo -e "${GREEN}Done. Updated $INSTALL_DST${NC}"
