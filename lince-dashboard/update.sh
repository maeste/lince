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
echo -e "${GREEN}[1/8] Building plugin...${NC}"
if ! "$SCRIPT_DIR/plugin/build.sh"; then
    echo -e "${RED}Build failed.${NC}"
    exit 1
fi
echo ""

# ── Plugin ─────────────────────────────────────────────────────────────
echo -e "${GREEN}[2/8] Updating plugin...${NC}"
PLUGIN_DIR="$HOME/.config/zellij/plugins"
mkdir -p "$PLUGIN_DIR"
cp "$SCRIPT_DIR/plugin/lince-dashboard.wasm" "$PLUGIN_DIR/lince-dashboard.wasm"
echo -e "${GREEN}  ✓ Plugin updated${NC}"
echo ""

# ── Layouts ────────────────────────────────────────────────────────────
echo -e "${GREEN}[3/8] Updating layouts...${NC}"
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

# ── Config ─────────────────────────────────────────────────────────────
echo -e "${GREEN}[4/8] Updating configuration...${NC}"
CONFIG_DIR="$HOME/.config/lince-dashboard"
CONFIG_DST="$CONFIG_DIR/config.toml"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DST" ]; then
    cp "$SCRIPT_DIR/config.toml" "$CONFIG_DST"
    echo -e "${GREEN}  ✓ Config installed${NC}"
else
    echo -e "${GREEN}  ✓ Existing config preserved${NC}"
fi
# Always refresh the shipped-defaults sidecar so users can diff against new
# upstream keys without losing their customizations:
#   diff -u "$CONFIG_DST.dist" "$CONFIG_DST"
cp "$SCRIPT_DIR/config.toml" "$CONFIG_DST.dist"
echo -e "${GREEN}  ✓ Upstream defaults available at config.toml.dist${NC}"
echo ""

# ── Hooks ──────────────────────────────────────────────────────────────
echo -e "${GREEN}[5/8] Updating agent platform hooks...${NC}"
if [ -f "$SCRIPT_DIR/hooks/update-hooks.sh" ]; then
    bash "$SCRIPT_DIR/hooks/update-hooks.sh"
else
    echo -e "${YELLOW}  ⚠ hooks/update-hooks.sh not found — run install.sh for first setup${NC}"
fi
echo ""

# ── Agent wrapper ─────────────────────────────────────────────────────
echo -e "${GREEN}[6/8] Updating agent wrapper...${NC}"
echo -e "${GREEN}  ✓ Managed by hooks/update-hooks.sh${NC}"
echo ""

# ── Agents defaults ──────────────────────────────────────────────────
echo -e "${GREEN}[7/8] Updating agent defaults...${NC}"
AGENTS_DEFAULTS_SRC="$SCRIPT_DIR/agents-defaults.toml"
AGENTS_DEFAULTS_DST="$CONFIG_DIR/agents-defaults.toml"

if [ -f "$AGENTS_DEFAULTS_SRC" ] && [ ! -f "$AGENTS_DEFAULTS_DST" ]; then
    cp "$AGENTS_DEFAULTS_SRC" "$AGENTS_DEFAULTS_DST"
    echo -e "${GREEN}  ✓ Agent defaults installed${NC}"
elif [ -f "$AGENTS_DEFAULTS_DST" ]; then
    echo -e "${GREEN}  ✓ Existing agent defaults preserved${NC}"
fi
# Always refresh the shipped-defaults sidecar (mirrors the config.toml.dist
# pattern above) so new upstream agent defaults stay discoverable:
#   diff -u "$AGENTS_DEFAULTS_DST.dist" "$AGENTS_DEFAULTS_DST"
if [ -f "$AGENTS_DEFAULTS_SRC" ]; then
    cp "$AGENTS_DEFAULTS_SRC" "$AGENTS_DEFAULTS_DST.dist"
    echo -e "${GREEN}  ✓ Upstream defaults available at agents-defaults.toml.dist${NC}"
fi
echo ""

# NOTE: new upstream keys are not auto-merged into preserved user files — by
# design, to avoid clobbering customizations. The .dist sidecars surface the
# diff. A tomlkit-based key-merge utility is tracked as follow-up in #108.

# ── Lince-add-supported-agent skill ──────────────────────────────────
echo -e "${GREEN}[8/8] Updating lince-add-supported-agent skill...${NC}"
SKILL_SRC="$SCRIPT_DIR/skills/lince-add-supported-agent"
SKILL_DST="$HOME/.claude/skills/lince-add-supported-agent"

if [ -d "$SKILL_SRC" ]; then
    mkdir -p "$SKILL_DST"
    cp -r "$SKILL_SRC/." "$SKILL_DST/"
    echo -e "${GREEN}  ✓ Skill updated${NC}"
fi

# Cleanup: remove the old skill dir from the previous skill name.
OLD_SKILL_DST="$HOME/.claude/skills/lince-setup"
if [ -d "$OLD_SKILL_DST" ]; then
    rm -rf "$OLD_SKILL_DST"
    echo -e "${GREEN}  ✓ Removed legacy ~/.claude/skills/lince-setup/${NC}"
fi
echo ""

# ── Sandbox check (informational only) ─────────────────────────────────
SANDBOX_CONFIG="$HOME/.agent-sandbox/config.toml"
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
elif [ ! -f "$HOME/.local/bin/agent-sandbox" ]; then
    true  # sandbox not installed, skip check
else
    echo -e "${YELLOW}NOTE: No sandbox config found. Run: cd ../sandbox && ./install.sh${NC}"
    echo ""
fi

echo -e "${GREEN}Update complete.${NC} Restart Zellij to load the new plugin."
echo ""
