#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   LINCE Dashboard — Update${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Ensure rustup toolchain takes precedence
export PATH="$HOME/.cargo/bin:$PATH"

# ── Build ──────────────────────────────────────────────────────────────
echo -e "${GREEN}[1/4] Building plugin...${NC}"
if ! "$SCRIPT_DIR/plugin/build.sh"; then
    echo -e "${RED}Build failed.${NC}"
    exit 1
fi
echo ""

# ── Plugin ─────────────────────────────────────────────────────────────
echo -e "${GREEN}[2/4] Updating plugin...${NC}"
PLUGIN_DIR="$HOME/.config/zellij/plugins"
mkdir -p "$PLUGIN_DIR"
cp "$SCRIPT_DIR/plugin/lince-dashboard.wasm" "$PLUGIN_DIR/lince-dashboard.wasm"
echo -e "${GREEN}  ✓ Plugin updated${NC}"
echo ""

# ── Layouts ────────────────────────────────────────────────────────────
echo -e "${GREEN}[3/4] Updating layouts...${NC}"
LAYOUT_DIR="$HOME/.config/zellij/layouts"
mkdir -p "$LAYOUT_DIR"
for layout in dashboard.kdl agent-single.kdl agent-multi.kdl; do
    SRC="$SCRIPT_DIR/layouts/$layout"
    if [ -f "$SRC" ]; then
        cp "$SRC" "$LAYOUT_DIR/$layout"
        echo -e "${GREEN}  ✓ $layout${NC}"
    fi
done
echo ""

# ── Hooks ──────────────────────────────────────────────────────────────
echo -e "${GREEN}[4/4] Updating hooks...${NC}"
HOOK_SRC="$SCRIPT_DIR/hooks/claude-status-hook.sh"
HOOK_DST="$HOME/.local/bin/claude-status-hook.sh"

if [ -f "$HOOK_SRC" ]; then
    mkdir -p "$HOME/.local/bin"
    cp "$HOOK_SRC" "$HOOK_DST"
    chmod +x "$HOOK_DST"
    echo -e "${GREEN}  ✓ Hook script updated${NC}"
fi

# Update Claude Code hooks in settings.json
# Events: Stop (→idle), UserPromptSubmit (→running), PreToolUse (→running), Notification (→various)
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ] && command -v jq >/dev/null 2>&1; then
    HOOK_CMD="claude-status-hook.sh"
    HOOK_ENTRY='{"matcher": "", "hooks": [{"type": "command", "command": "'"$HOOK_CMD"'"}]}'

    # Idempotent: for each event, add our entry only if not already present (correct format)
    # Also removes any old-format entries (missing "matcher" key) for our command
    UPDATED=$(jq --arg cmd "$HOOK_CMD" --argjson entry "$HOOK_ENTRY" '
        .hooks //= {} |
        reduce ("Stop", "UserPromptSubmit", "PreToolUse", "Notification") as $event (.;
            .hooks[$event] = [.hooks[$event][]? | select(has("matcher"))] |
            if (.hooks[$event] | map(select(.hooks[]?.command == $cmd)) | length) == 0
            then .hooks[$event] = ((.hooks[$event] // []) + [$entry])
            else . end
        )
    ' "$SETTINGS" 2>/dev/null)

    if [ -n "$UPDATED" ]; then
        echo "$UPDATED" > "$SETTINGS"
        echo -e "${GREEN}  ✓ Hooks configured (Stop, UserPromptSubmit, PreToolUse, Notification)${NC}"
    else
        echo -e "${YELLOW}  ⚠ Could not update settings.json — check jq version${NC}"
    fi
else
    echo -e "${YELLOW}  settings.json or jq not found — run install.sh for first setup${NC}"
fi
echo ""

# ── Sandbox check (informational only) ─────────────────────────────────
SANDBOX_CONFIG="$HOME/.claude-sandbox/config.toml"
if [ -f "$SANDBOX_CONFIG" ]; then
    MISSING=false
    for var in ZELLIJ ZELLIJ_SESSION_NAME LINCE_AGENT_ID; do
        if ! python3 -c "
import tomllib, sys
with open(sys.argv[1], 'rb') as f:
    cfg = tomllib.load(f)
sys.exit(0 if sys.argv[2] in cfg.get('env', {}).get('passthrough', []) else 1)
" "$SANDBOX_CONFIG" "$var" 2>/dev/null; then
            MISSING=true
            break
        fi
    done
    if [ "$MISSING" = true ]; then
        echo -e "${YELLOW}NOTE: Sandbox env passthrough missing ZELLIJ/LINCE_AGENT_ID vars.${NC}"
        echo -e "${YELLOW}  Run: cd ../sandbox && ./update.sh${NC}"
        echo ""
    fi
elif [ ! -f "$HOME/.local/bin/claude-sandbox" ]; then
    true  # sandbox not installed, skip check
else
    echo -e "${YELLOW}NOTE: No sandbox config found. Run: cd ../sandbox && ./install.sh${NC}"
    echo ""
fi

echo -e "${GREEN}Update complete.${NC} Restart Zellij to load the new plugin."
echo ""
