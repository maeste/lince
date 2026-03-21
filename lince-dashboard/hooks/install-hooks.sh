#!/usr/bin/env bash
# install-hooks.sh — Install claude-status-hook.sh into Claude Code hooks config.
#
# What it does:
#   1. Copies the hook script to ~/.local/bin/
#   2. Updates ~/.claude/settings.json with hook entries for Stop, PreToolUse, Notification
#   3. Prints sandbox env passthrough requirements
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
SETTINGS_FILE="$HOME/.claude/settings.json"

# Check prerequisites
if ! command -v jq >/dev/null 2>&1; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    echo "Install with: sudo dnf install jq  (or: sudo apt-get install jq)"
    exit 1
fi

if [ ! -f "$HOOK_SRC" ]; then
    echo -e "${RED}Error: Hook script not found at $HOOK_SRC${NC}"
    exit 1
fi

echo -e "${GREEN}[1/3] Installing hook script...${NC}"
mkdir -p "$HOME/.local/bin"
cp "$HOOK_SRC" "$HOOK_DEST"
chmod +x "$HOOK_DEST"
echo -e "${GREEN}  Installed: $HOOK_DEST${NC}"

echo ""
echo -e "${GREEN}[2/3] Configuring Claude Code hooks...${NC}"

# Create settings.json if it doesn't exist
mkdir -p "$HOME/.claude"
if [ ! -f "$SETTINGS_FILE" ]; then
    echo '{}' > "$SETTINGS_FILE"
    echo "  Created $SETTINGS_FILE"
fi

# Define the hooks we need to add
# Claude Code hooks format: { "hooks": { "<event>": [{ "type": "command", "command": "..." }] } }
HOOK_CMD="claude-status-hook.sh"
HOOK_ENTRY='{"matcher": "", "hooks": [{"type": "command", "command": "'"$HOOK_CMD"'"}]}'

# Idempotent merge: add our hook to each event only if not already present.
# Covers all events needed for accurate status tracking:
#   Stop             → agent finished turn, waiting for input
#   UserPromptSubmit → user sent a message, agent is now running
#   PreToolUse       → agent is using a tool (already running)
#   Notification     → idle_prompt / permission_prompt
MERGED=$(jq --arg cmd "$HOOK_CMD" --argjson entry "$HOOK_ENTRY" '
    .hooks //= {} |
    reduce ("Stop", "UserPromptSubmit", "PreToolUse", "Notification") as $event (.;
        .hooks[$event] = [.hooks[$event][]? | select(has("matcher"))] |
        if (.hooks[$event] | map(select(.hooks[]?.command == $cmd)) | length) == 0
        then .hooks[$event] = ((.hooks[$event] // []) + [$entry])
        else . end
    )
' "$SETTINGS_FILE")

if [ -n "$MERGED" ]; then
    echo "$MERGED" > "$SETTINGS_FILE"
    echo -e "${GREEN}  ✓ Hooks configured: Stop, UserPromptSubmit, PreToolUse, Notification${NC}"
else
    echo -e "${YELLOW}  ⚠ Could not update settings.json — check jq version${NC}"
fi

echo ""
echo -e "${GREEN}[3/3] Sandbox configuration requirements${NC}"
echo ""
echo -e "${YELLOW}  IMPORTANT: For hooks to work inside claude-sandbox, you must${NC}"
echo -e "${YELLOW}  add these environment variables to your sandbox config passthrough:${NC}"
echo ""
echo "  In ~/.claude-sandbox/config.toml (or project-local .claude-sandbox/config.toml):"
echo ""
echo '  [env]'
echo '  passthrough = ["ZELLIJ", "ZELLIJ_SESSION_NAME", "LINCE_AGENT_ID"]'
echo ""
echo -e "${GREEN}Installation complete.${NC}"
echo ""
echo "Hook script: $HOOK_DEST"
echo "Settings:    $SETTINGS_FILE"
echo ""
echo "To verify:"
echo "  echo '{\"hook_event_name\":\"Stop\"}' | LINCE_AGENT_ID=test-1 bash $HOOK_DEST"
echo "  cat /tmp/claude-test-1.state  # should show: stopped"
