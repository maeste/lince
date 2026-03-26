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

# ── Hook scripts ───────────────────────────────────────────────────────
HOOKS=(
    "$HOME/.local/bin/claude-status-hook.sh"
    "$HOME/.local/bin/codex-status-hook.sh"
)
FOUND_HOOKS=()
for hook in "${HOOKS[@]}"; do
    [ -f "$hook" ] && FOUND_HOOKS+=("$hook")
done

if [ ${#FOUND_HOOKS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Found hook scripts:${NC}"
    for hook in "${FOUND_HOOKS[@]}"; do
        echo "  $hook"
    done
    if confirm "  Remove hook scripts?"; then
        rm -f "${FOUND_HOOKS[@]}"
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Hook scripts not found — skipping"
fi
echo ""

# ── Agent wrapper ─────────────────────────────────────────────────────
WRAPPER="$HOME/.local/bin/lince-agent-wrapper"
if [ -f "$WRAPPER" ]; then
    echo -e "${YELLOW}Found: $WRAPPER${NC}"
    if confirm "  Remove agent wrapper?"; then
        rm -f "$WRAPPER"
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Agent wrapper not found — skipping"
fi
echo ""

# ── Agent defaults ────────────────────────────────────────────────────
AGENTS_DEFAULTS="$HOME/.config/lince-dashboard/agents-defaults.toml"
if [ -f "$AGENTS_DEFAULTS" ]; then
    echo -e "${YELLOW}Found: $AGENTS_DEFAULTS${NC}"
    if confirm "  Remove agent defaults?"; then
        rm -f "$AGENTS_DEFAULTS"
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Agent defaults not found — skipping"
fi
echo ""

# ── Lince-setup skill ────────────────────────────────────────────────
SKILL_DIR="$HOME/.claude/skills/lince-setup"
if [ -d "$SKILL_DIR" ]; then
    echo -e "${YELLOW}Found: $SKILL_DIR${NC}"
    if confirm "  Remove lince-setup skill?"; then
        rm -rf "$SKILL_DIR"
        echo -e "${GREEN}  ✓ Removed${NC}"
    fi
else
    echo "  Lince-setup skill not found — skipping"
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

# ── Codex notify in config.toml ────────────────────────────────────────
CODEX_CONFIG="$HOME/.codex/config.toml"
CODEX_BLOCK_START="# >>> LINCE Dashboard Codex notify >>>"
CODEX_BLOCK_END="# <<< LINCE Dashboard Codex notify <<<"
if [ -f "$CODEX_CONFIG" ]; then
    if grep -Fq "$CODEX_BLOCK_START" "$CODEX_CONFIG"; then
        echo -e "${YELLOW}Found dashboard Codex notify block in $CODEX_CONFIG${NC}"
        if confirm "  Remove Codex notify block?"; then
            TMP_FILE="$(mktemp)"
            awk -v start="$CODEX_BLOCK_START" -v end="$CODEX_BLOCK_END" '
                $0 == start { skipping=1; next }
                $0 == end { skipping=0; next }
                !skipping { print }
            ' "$CODEX_CONFIG" > "$TMP_FILE"
            mv "$TMP_FILE" "$CODEX_CONFIG"
            echo -e "${GREEN}  ✓ Removed Codex notify block${NC}"
        fi
    else
        echo "  No dashboard Codex notify block found — skipping"
    fi
else
    echo "  Codex config not found — skipping notify cleanup"
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
STATUS_DIR_EXISTS=false
[ -d "/tmp/lince-dashboard" ] && STATUS_DIR_EXISTS=true

if [ -n "$STATUS_FILES" ] || [ "$STATUS_DIR_EXISTS" = true ]; then
    echo -e "${YELLOW}Found status files in /tmp/${NC}"
    if confirm "  Remove status files?"; then
        rm -f /tmp/claude-agent-*.state
        rm -rf /tmp/lince-dashboard
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
