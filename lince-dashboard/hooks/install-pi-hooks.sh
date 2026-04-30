#!/usr/bin/env bash
# install-pi-hooks.sh — Install Pi extension that emits status events to lince-dashboard.
#
# What it does:
#   1. Copies lince-pi-hook.ts to ~/.pi/agent/extensions/
#   2. Copies the shared agent wrapper to ~/.local/bin/ (used by non-native-hook agents)
#   3. Prints sandbox env passthrough requirements
#
# Pi auto-discovers extensions from ~/.pi/agent/extensions/*.ts at startup,
# so no settings.json edit is required.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SRC="$SCRIPT_DIR/pi/lince-pi-hook.ts"
HOOK_DEST_DIR="$HOME/.pi/agent/extensions"
HOOK_DEST="$HOOK_DEST_DIR/lince-pi-hook.ts"
WRAPPER_SRC="$SCRIPT_DIR/lince-agent-wrapper"
WRAPPER_DEST="$HOME/.local/bin/lince-agent-wrapper"

if [ ! -f "$HOOK_SRC" ]; then
    echo -e "${RED}Error: Hook script not found at $HOOK_SRC${NC}"
    exit 1
fi

echo -e "${GREEN}[1/3] Installing Pi extension...${NC}"
mkdir -p "$HOOK_DEST_DIR"
cp "$HOOK_SRC" "$HOOK_DEST"
echo -e "${GREEN}  Installed: $HOOK_DEST${NC}"

echo ""
echo -e "${GREEN}[2/3] Installing shared agent wrapper...${NC}"
if [ -f "$WRAPPER_SRC" ]; then
    mkdir -p "$HOME/.local/bin"
    cp "$WRAPPER_SRC" "$WRAPPER_DEST"
    chmod +x "$WRAPPER_DEST"
    echo -e "${GREEN}  Installed: $WRAPPER_DEST${NC}"
else
    echo -e "${YELLOW}  ⚠ lince-agent-wrapper not found at $WRAPPER_SRC — skipping${NC}"
fi

echo ""
echo -e "${GREEN}[3/3] Sandbox configuration requirements${NC}"
echo ""
echo -e "${YELLOW}  IMPORTANT: For Pi status events to work inside agent-sandbox, you must${NC}"
echo -e "${YELLOW}  add these environment variables to your sandbox config passthrough:${NC}"
echo ""
echo "  In ~/.agent-sandbox/config.toml (or project-local .agent-sandbox/config.toml):"
echo ""
echo '  [env]'
echo '  passthrough = ["ZELLIJ", "ZELLIJ_SESSION_NAME", "LINCE_AGENT_ID"]'
echo ""
echo -e "${GREEN}Pi hook installation complete.${NC}"
echo ""
echo "Extension: $HOOK_DEST"
echo ""
echo "Pi auto-discovers extensions in ~/.pi/agent/extensions/ on startup."
echo "Verify with:"
echo "  pi --version  # confirm pi is installed"
echo "  ls $HOOK_DEST"
