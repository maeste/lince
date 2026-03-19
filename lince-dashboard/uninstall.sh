#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   LINCE Dashboard — Uninstaller${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ── Plugin ─────────────────────────────────────────────────────────────
PLUGIN="$HOME/.config/zellij/plugins/lince-dashboard.wasm"
if [ -f "$PLUGIN" ]; then
    echo -e "${YELLOW}Found: $PLUGIN${NC}"
    if confirm "  Remove plugin?"; then
        rm -f "$PLUGIN" "${PLUGIN}.bak."* 2>/dev/null
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Plugin not found — skipping"
fi
echo ""

# ── Layouts ────────────────────────────────────────────────────────────
LAYOUT_DIR="$HOME/.config/zellij/layouts"
LAYOUTS=("dashboard.kdl" "agent-single.kdl" "agent-multi.kdl")
FOUND_LAYOUTS=()
for l in "${LAYOUTS[@]}"; do
    [ -f "$LAYOUT_DIR/$l" ] && FOUND_LAYOUTS+=("$l")
done

if [ ${#FOUND_LAYOUTS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Found layouts: ${FOUND_LAYOUTS[*]}${NC}"
    if confirm "  Remove layouts?"; then
        for l in "${FOUND_LAYOUTS[@]}"; do
            rm -f "$LAYOUT_DIR/$l"
        done
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  No dashboard layouts found — skipping"
fi
echo ""

# ── Config ─────────────────────────────────────────────────────────────
CONFIG_DIR="$HOME/.config/lince-dashboard"
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}Found: $CONFIG_DIR${NC}"
    if confirm "  Remove config directory?"; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Config directory not found — skipping"
fi
echo ""

# ── Hook script ────────────────────────────────────────────────────────
HOOK="$HOME/.local/bin/claude-status-hook.sh"
if [ -f "$HOOK" ]; then
    echo -e "${YELLOW}Found: $HOOK${NC}"
    if confirm "  Remove hook script?"; then
        rm -f "$HOOK"
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Hook script not found — skipping"
fi
echo ""

# ── Claude Code hooks in settings.json ─────────────────────────────────
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ] && command -v jq >/dev/null 2>&1; then
    if jq -e '.hooks.Stop[]? | select(.command == "claude-status-hook.sh")' "$SETTINGS" >/dev/null 2>&1; then
        echo -e "${YELLOW}Found dashboard hooks in $SETTINGS${NC}"
        if confirm "  Remove hook entries from Claude Code settings?"; then
            UPDATED=$(jq '
                .hooks.Stop = [.hooks.Stop[]? | select(.command != "claude-status-hook.sh")] |
                .hooks.PreToolUse = [.hooks.PreToolUse[]? | select(.command != "claude-status-hook.sh")] |
                .hooks.Notification = [.hooks.Notification[]? | select(.command != "claude-status-hook.sh")] |
                if .hooks.Stop == [] then del(.hooks.Stop) else . end |
                if .hooks.PreToolUse == [] then del(.hooks.PreToolUse) else . end |
                if .hooks.Notification == [] then del(.hooks.Notification) else . end |
                if .hooks == {} then del(.hooks) else . end
            ' "$SETTINGS")
            echo "$UPDATED" > "$SETTINGS"
            echo -e "${GREEN}  ✓ Removed hook entries${NC}"
        fi
    else
        echo "  No dashboard hooks in settings.json — skipping"
    fi
else
    echo "  Settings.json not found or jq missing — skipping hook cleanup"
fi
echo ""

# ── Shell alias ────────────────────────────────────────────────────────
ALIAS_REMOVED=false
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ] && grep -q 'alias zd=' "$rc" 2>/dev/null; then
        echo -e "${YELLOW}Found 'zd' alias in $(basename $rc)${NC}"
        if confirm "  Remove alias?"; then
            # Remove the alias line and its comment
            sed -i '/# LINCE Dashboard alias/d' "$rc"
            sed -i '/alias zd=/d' "$rc"
            ALIAS_REMOVED=true
            echo -e "${GREEN}  ✓ Removed from $(basename $rc)${NC}"
        fi
    fi
done
if [ "$ALIAS_REMOVED" = false ]; then
    echo "  No 'zd' alias found — skipping"
fi
echo ""

# ── Status files ───────────────────────────────────────────────────────
STATUS_FILES=$(ls /tmp/claude-agent-*.state 2>/dev/null || true)
if [ -n "$STATUS_FILES" ]; then
    echo -e "${YELLOW}Found status files in /tmp/${NC}"
    if confirm "  Remove status files?"; then
        rm -f /tmp/claude-agent-*.state
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
fi
echo ""

# ── Done ───────────────────────────────────────────────────────────────
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Uninstall Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Source files in lince-dashboard/ were NOT removed."
echo "To reinstall later: cd lince-dashboard && ./install.sh"
echo ""
