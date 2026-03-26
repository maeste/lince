#!/usr/bin/env bash
# install-opencode-hooks.sh — Install OpenCode plugin for lince-dashboard integration.
#
# What it does:
#   1. Copies the status plugin to ~/.config/opencode/plugins/ (auto-loaded by opencode)
#   2. Copies the shared agent wrapper to ~/.local/bin/
#   3. Cleans up any stale "plugins" key from opencode.json (previous installs)
#   4. Prints sandbox env passthrough requirements
#
# Requirements:
#   - node (for ES module support)
#   - OpenCode installed (~/.config/opencode/ directory exists or will be created)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SRC="$SCRIPT_DIR/opencode-status-hook.js"
PLUGIN_DEST_DIR="$HOME/.config/opencode/plugins"
PLUGIN_DEST="$PLUGIN_DEST_DIR/opencode-status-hook.js"
WRAPPER_SRC="$SCRIPT_DIR/lince-agent-wrapper"
WRAPPER_DEST="$HOME/.local/bin/lince-agent-wrapper"
CONFIG_DIR="$HOME/.config/opencode"
CONFIG_FILE="$CONFIG_DIR/opencode.json"

if ! command -v node >/dev/null 2>&1; then
    echo -e "${RED}Error: node is required but not installed.${NC}"
    echo "Install with: sudo dnf install nodejs  (or: brew install node)"
    exit 1
fi

if [ ! -f "$HOOK_SRC" ]; then
    echo -e "${RED}Error: OpenCode plugin not found at $HOOK_SRC${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4] Installing OpenCode status plugin...${NC}"
mkdir -p "$PLUGIN_DEST_DIR"
cp "$HOOK_SRC" "$PLUGIN_DEST"
chmod +x "$PLUGIN_DEST"
echo -e "${GREEN}  Installed: $PLUGIN_DEST${NC}"

echo ""
echo -e "${GREEN}[2/4] Installing shared agent wrapper...${NC}"
if [ -f "$WRAPPER_SRC" ]; then
    mkdir -p "$HOME/.local/bin"
    cp "$WRAPPER_SRC" "$WRAPPER_DEST"
    chmod +x "$WRAPPER_DEST"
    echo -e "${GREEN}  Installed: $WRAPPER_DEST${NC}"
else
    echo -e "${YELLOW}  ⚠ lince-agent-wrapper not found at $WRAPPER_SRC — skipping${NC}"
fi

echo ""
echo -e "${GREEN}[3/4] Verifying OpenCode plugin auto-load directory...${NC}"
echo -e "${GREEN}  ✓ OpenCode auto-loads plugins from $PLUGIN_DEST_DIR — no config edit needed${NC}"

# Clean up any stale "plugins" key from previous installs that breaks opencode
if [ -f "$CONFIG_FILE" ]; then
    if command -v jq >/dev/null 2>&1; then
        if jq -e '.plugins' "$CONFIG_FILE" >/dev/null 2>&1; then
            CLEANED=$(jq 'del(.plugins)' "$CONFIG_FILE" 2>/dev/null) || CLEANED=""
            if [ -n "$CLEANED" ]; then
                echo "$CLEANED" > "$CONFIG_FILE"
                echo -e "${YELLOW}  ⚠ Removed stale \"plugins\" key from $CONFIG_FILE (was causing startup error)${NC}"
            fi
        fi
    elif grep -q '"plugins"' "$CONFIG_FILE" 2>/dev/null; then
        echo -e "${YELLOW}  ⚠ $CONFIG_FILE may contain a stale \"plugins\" key — install jq to auto-clean, or remove it manually${NC}"
    fi
fi

echo ""
echo -e "${GREEN}[4/4] Sandbox configuration requirements${NC}"
echo ""
echo -e "${YELLOW}  IMPORTANT: For OpenCode status updates to work inside agent-sandbox, you must${NC}"
echo -e "${YELLOW}  add these environment variables to your sandbox config passthrough:${NC}"
echo ""
echo "  In ~/.agent-sandbox/config.toml (or project-local .agent-sandbox/config.toml):"
echo ""
echo '  [env]'
echo '  passthrough = ["ZELLIJ", "ZELLIJ_SESSION_NAME", "LINCE_AGENT_ID"]'
echo ""
echo -e "${GREEN}OpenCode hook installation complete.${NC}"
echo ""
echo "Plugin script: $PLUGIN_DEST"
echo "Plugin dir:    $PLUGIN_DEST_DIR (auto-loaded by opencode)"
echo ""
echo "To verify:"
echo "  LINCE_AGENT_ID=test-1 node $PLUGIN_DEST"
echo "  cat /tmp/lince-dashboard/opencode-test-1.state  # should show: running"
