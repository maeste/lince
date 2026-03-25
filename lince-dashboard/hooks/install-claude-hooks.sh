#!/usr/bin/env bash
# install-claude-hooks.sh — Install hooks and agent wrapper into Claude Code config.
#
# What it does:
#   1. Copies the hook script to ~/.local/bin/
#   2. Copies the agent wrapper to ~/.local/bin/
#   3. Updates ~/.claude/settings.json with hook entries for Stop, PreToolUse, Notification
#   4. Prints sandbox env passthrough requirements
#
# Requirements:
#   - jq (for JSON manipulation)
#   - Claude Code installed (~/.claude/ directory exists)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SRC="$SCRIPT_DIR/claude-status-hook.sh"
HOOK_DEST="$HOME/.local/bin/claude-status-hook.sh"
WRAPPER_SRC="$SCRIPT_DIR/lince-agent-wrapper"
WRAPPER_DEST="$HOME/.local/bin/lince-agent-wrapper"
SETTINGS_FILE="$HOME/.claude/settings.json"

if ! command -v jq >/dev/null 2>&1; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    echo "Install with: sudo dnf install jq  (or: sudo apt-get install jq)"
    exit 1
fi

if [ ! -f "$HOOK_SRC" ]; then
    echo -e "${RED}Error: Hook script not found at $HOOK_SRC${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4] Installing Claude hook script...${NC}"
mkdir -p "$HOME/.local/bin"
cp "$HOOK_SRC" "$HOOK_DEST"
chmod +x "$HOOK_DEST"
echo -e "${GREEN}  Installed: $HOOK_DEST${NC}"

echo ""
echo -e "${GREEN}[2/4] Installing shared agent wrapper...${NC}"
if [ -f "$WRAPPER_SRC" ]; then
    cp "$WRAPPER_SRC" "$WRAPPER_DEST"
    chmod +x "$WRAPPER_DEST"
    echo -e "${GREEN}  Installed: $WRAPPER_DEST${NC}"
else
    echo -e "${YELLOW}  ⚠ lince-agent-wrapper not found at $WRAPPER_SRC — skipping${NC}"
fi

echo ""
echo -e "${GREEN}[3/4] Configuring Claude Code hooks...${NC}"

mkdir -p "$HOME/.claude"
if [ ! -f "$SETTINGS_FILE" ]; then
    echo '{}' > "$SETTINGS_FILE"
    echo "  Created $SETTINGS_FILE"
fi

HOOK_CMD="claude-status-hook.sh"
HOOK_ENTRY='{"matcher": "", "hooks": [{"type": "command", "command": "'"$HOOK_CMD"'"}]}'

MERGED=$(jq --arg cmd "$HOOK_CMD" --argjson entry "$HOOK_ENTRY" '
    .hooks //= {} |
    reduce ("SessionStart", "Stop", "UserPromptSubmit", "PreToolUse", "Notification") as $event (.;
        .hooks[$event] = [.hooks[$event][]? | select(has("matcher"))] |
        if (.hooks[$event] | map(select(.hooks[]?.command == $cmd)) | length) == 0
        then .hooks[$event] = ((.hooks[$event] // []) + [$entry])
        else . end
    )
' "$SETTINGS_FILE")

if [ -n "$MERGED" ]; then
    echo "$MERGED" > "$SETTINGS_FILE"
    echo -e "${GREEN}  ✓ Hooks configured: SessionStart, Stop, UserPromptSubmit, PreToolUse, Notification${NC}"
else
    echo -e "${YELLOW}  ⚠ Could not update settings.json — check jq version${NC}"
fi

echo ""
echo -e "${GREEN}[4/4] Sandbox configuration requirements${NC}"
echo ""
echo -e "${YELLOW}  IMPORTANT: For hooks to work inside agent-sandbox, you must${NC}"
echo -e "${YELLOW}  add these environment variables to your sandbox config passthrough:${NC}"
echo ""
echo "  In ~/.agent-sandbox/config.toml (or project-local .agent-sandbox/config.toml):"
echo ""
echo '  [env]'
echo '  passthrough = ["ZELLIJ", "ZELLIJ_SESSION_NAME", "LINCE_AGENT_ID"]'
echo ""
echo -e "${GREEN}Claude hook installation complete.${NC}"
echo ""
echo "Hook script: $HOOK_DEST"
echo "Settings:    $SETTINGS_FILE"
echo ""
echo "To verify:"
echo "  echo '{\"hook_event_name\":\"Stop\"}' | LINCE_AGENT_ID=test-1 bash $HOOK_DEST"
echo "  cat /tmp/lince-dashboard/claude-test-1.state  # should show: idle"
