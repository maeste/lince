#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   LINCE Dashboard — Installer${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ── Step 1: Prerequisites ─────────────────────────────────────────────
echo -e "${GREEN}[1/12] Checking prerequisites...${NC}"

MISSING=()

if ! command -v zellij >/dev/null 2>&1; then
    MISSING+=("zellij (>= 0.40)")
else
    echo -e "${GREEN}  ✓ zellij $(zellij --version 2>/dev/null | awk '{print $2}')${NC}"
fi

if ! command -v rustc >/dev/null 2>&1; then
    MISSING+=("rustc")
else
    echo -e "${GREEN}  ✓ rustc $(rustc --version 2>/dev/null | awk '{print $2}')${NC}"
fi

if ! command -v cargo >/dev/null 2>&1; then
    MISSING+=("cargo")
else
    echo -e "${GREEN}  ✓ cargo${NC}"
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${RED}Missing prerequisites:${NC}"
    for m in "${MISSING[@]}"; do
        echo "  - $m"
    done
    echo ""
    echo "Install them first, then re-run this script."
    exit 1
fi
echo ""

# ── Step 2: WASM target ───────────────────────────────────────────────
echo -e "${GREEN}[2/12] Checking wasm32-wasip1 target...${NC}"

# Ensure rustup toolchain takes precedence
export PATH="$HOME/.cargo/bin:$PATH"

if command -v rustup >/dev/null 2>&1; then
    if ! rustup target list --installed 2>/dev/null | grep -q wasm32-wasip1; then
        echo "  Installing wasm32-wasip1 target..."
        rustup target add wasm32-wasip1
    fi
    echo -e "${GREEN}  ✓ wasm32-wasip1 target installed${NC}"
else
    echo -e "${YELLOW}  ⚠ rustup not found — assuming wasm32-wasip1 is available${NC}"
fi
echo ""

# ── Step 3: Build plugin ──────────────────────────────────────────────
echo -e "${GREEN}[3/12] Building plugin...${NC}"

if ! "$SCRIPT_DIR/plugin/build.sh"; then
    echo -e "${RED}Build failed. Check errors above.${NC}"
    exit 1
fi
echo ""

# ── Step 4: Install WASM plugin ───────────────────────────────────────
echo -e "${GREEN}[4/12] Installing plugin...${NC}"

PLUGIN_DIR="$HOME/.config/zellij/plugins"
mkdir -p "$PLUGIN_DIR"

WASM_SRC="$SCRIPT_DIR/plugin/lince-dashboard.wasm"
WASM_DST="$PLUGIN_DIR/lince-dashboard.wasm"

if [ -f "$WASM_DST" ]; then
    echo -e "${YELLOW}  Existing plugin found, backing up...${NC}"
    cp "$WASM_DST" "${WASM_DST}.bak.$(date +%Y%m%d_%H%M%S)"
fi

cp "$WASM_SRC" "$WASM_DST"
echo -e "${GREEN}  ✓ Installed: $WASM_DST${NC}"

# Pre-grant Zellij permissions so the plugin works without interactive prompt.
# Zellij caches granted permissions in ~/.cache/zellij/permissions.kdl.
PERMS_CACHE="$HOME/.cache/zellij/permissions.kdl"
mkdir -p "$HOME/.cache/zellij"
if [ -f "$PERMS_CACHE" ] && grep -q "lince-dashboard.wasm" "$PERMS_CACHE" 2>/dev/null; then
    echo -e "${GREEN}  ✓ Plugin permissions already cached${NC}"
else
    cat >> "$PERMS_CACHE" << PERMSEOF
"${WASM_DST}" {
    RunCommands
    ReadApplicationState
    ReadCliPipes
    WriteToStdin
    ChangeApplicationState
    OpenTerminalsOrPlugins
    MessageAndLaunchOtherPlugins
}
PERMSEOF
    echo -e "${GREEN}  ✓ Plugin permissions pre-granted${NC}"
fi
echo ""

# ── Step 5: Install layouts ───────────────────────────────────────────
echo -e "${GREEN}[5/12] Installing layouts...${NC}"

LAYOUT_DIR="$HOME/.config/zellij/layouts"
mkdir -p "$LAYOUT_DIR"

for layout in dashboard.kdl dashboard-vox.kdl agent-single.kdl agent-multi.kdl; do
    SRC="$SCRIPT_DIR/layouts/$layout"
    DST="$LAYOUT_DIR/$layout"
    if [ -f "$SRC" ]; then
        cp "$SRC" "$DST"
        echo -e "${GREEN}  ✓ $layout${NC}"
    fi
done
echo ""

# ── Step 6: Zellij keybinding configuration ──────────────────────────
echo -e "${GREEN}[6/12] Zellij keybinding configuration...${NC}"

ZELLIJ_CONFIG="$HOME/.config/zellij/config.kdl"
LINCE_ZELLIJ_CONFIG="$SCRIPT_DIR/zellij-config/config.kdl"

if [ -f "$LINCE_ZELLIJ_CONFIG" ]; then
    if [ -f "$ZELLIJ_CONFIG" ]; then
        echo -e "${YELLOW}  Existing Zellij config found: $ZELLIJ_CONFIG${NC}"
        echo ""
        echo "  LINCE includes keybindings optimized for AI coding agents"
        echo "  (Ctrl+O disabled to avoid conflicts, custom mode bindings)."
        echo "  Your current config will be backed up."
        echo ""
        if confirm "  Install LINCE keybindings?"; then
            BACKUP="${ZELLIJ_CONFIG}.bak.$(date +%Y%m%d_%H%M%S)"
            cp "$ZELLIJ_CONFIG" "$BACKUP"
            echo -e "${GREEN}  ✓ Backup: $BACKUP${NC}"
            cp "$LINCE_ZELLIJ_CONFIG" "$ZELLIJ_CONFIG"
            echo -e "${GREEN}  ✓ LINCE keybindings installed${NC}"
        else
            echo -e "${YELLOW}  Skipped — keeping your existing config${NC}"
            echo -e "${YELLOW}  Note: some keybindings may conflict with AI coding agents${NC}"
        fi
    else
        echo "  No existing Zellij config found."
        if confirm "  Install LINCE keybindings? (Ctrl+O disabled for agent compatibility)"; then
            mkdir -p "$(dirname "$ZELLIJ_CONFIG")"
            cp "$LINCE_ZELLIJ_CONFIG" "$ZELLIJ_CONFIG"
            echo -e "${GREEN}  ✓ LINCE keybindings installed${NC}"
        else
            echo -e "${YELLOW}  Skipped${NC}"
        fi
    fi
else
    echo -e "${YELLOW}  ⚠ zellij-config/config.kdl not found — skipping${NC}"
fi
echo ""

# ── Step 7: Install config ────────────────────────────────────────────
echo -e "${GREEN}[7/12] Installing configuration...${NC}"

CONFIG_DIR="$HOME/.config/lince-dashboard"
CONFIG_DST="$CONFIG_DIR/config.toml"

mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_DST" ]; then
    BACKUP="${CONFIG_DST}.bak.$(date +%Y%m%d_%H%M%S)"
    cp "$CONFIG_DST" "$BACKUP"
    echo -e "${YELLOW}  Existing config backed up → $(basename "$BACKUP")${NC}"
fi
cp "$SCRIPT_DIR/config.toml" "$CONFIG_DST"
echo -e "${GREEN}  ✓ Installed: $CONFIG_DST${NC}"
echo ""

# ── Step 8: Install hooks ─────────────────────────────────────────────
echo -e "${GREEN}[8/12] Installing agent platform hooks...${NC}"

if [ -f "$SCRIPT_DIR/hooks/install-hooks.sh" ]; then
    bash "$SCRIPT_DIR/hooks/install-hooks.sh"
else
    echo -e "${YELLOW}  ⚠ hooks/install-hooks.sh not found — skipping${NC}"
fi
echo ""

# ── Step 9: Install agents-defaults.toml ─────────────────────────────
echo -e "${GREEN}[9/12] Installing agent defaults...${NC}"

AGENTS_DEFAULTS_SRC="$SCRIPT_DIR/agents-defaults.toml"
AGENTS_DEFAULTS_DST="$CONFIG_DIR/agents-defaults.toml"

if [ -f "$AGENTS_DEFAULTS_SRC" ]; then
    cp "$AGENTS_DEFAULTS_SRC" "$AGENTS_DEFAULTS_DST"
    echo -e "${GREEN}  ✓ Installed: $AGENTS_DEFAULTS_DST${NC}"
else
    echo -e "${YELLOW}  ⚠ agents-defaults.toml not found — skipping${NC}"
fi
echo ""

# ── Step 10: Install lince-setup skill ────────────────────────────────
echo -e "${GREEN}[10/12] Installing lince-setup skill...${NC}"

SKILL_SRC="$SCRIPT_DIR/skills/lince-setup"
SKILL_DST="$HOME/.claude/skills/lince-setup"

if [ -d "$SKILL_SRC" ]; then
    mkdir -p "$SKILL_DST"
    cp -r "$SKILL_SRC/." "$SKILL_DST/"
    echo -e "${GREEN}  ✓ Installed: $SKILL_DST${NC}"
else
    echo -e "${YELLOW}  ⚠ skills/lince-setup/ not found — skipping${NC}"
fi
echo ""

# ── Step 11: Shell aliases ────────────────────────────────────────────
echo -e "${GREEN}[11/12] Setting up shell aliases...${NC}"

ALIAS_LINES='alias zd="zellij --layout dashboard"
alias z="zellij"
alias zn="zellij attach -c"'
ALIAS_COMMENT="# LINCE aliases"

for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ]; then
        if grep -q "# LINCE aliases" "$rc" 2>/dev/null; then
            echo -e "${YELLOW}  LINCE aliases already in $(basename $rc)${NC}"
        else
            echo "" >> "$rc"
            echo "$ALIAS_COMMENT" >> "$rc"
            echo "$ALIAS_LINES" >> "$rc"
            echo -e "${GREEN}  ✓ Added aliases (zd, z, zn) to $(basename $rc)${NC}"
        fi
    fi
done
echo ""

# ── Step 12: VoxCode layout selection ─────────────────────────────────
echo -e "${GREEN}[12/12] VoxCode layout configuration...${NC}"

if command -v voxcode >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ voxcode detected${NC}"
    echo "  Setting dashboard-vox.kdl as default layout (includes VoxCode pane)."
    if [ -f "$LAYOUT_DIR/dashboard-vox.kdl" ]; then
        cp "$LAYOUT_DIR/dashboard-vox.kdl" "$LAYOUT_DIR/dashboard.kdl"
        echo -e "${GREEN}  ✓ Dashboard layout updated with VoxCode pane${NC}"
    fi
else
    echo -e "${YELLOW}  VoxCode not found — using standard dashboard layout${NC}"
    echo "  For voice input, install VoxCode separately:"
    echo "    https://github.com/RisorseArtificiali/voxcode"
fi
echo ""

# ── Sandbox backend check ─────────────────────────────────────────────
echo -e "${GREEN}[post] Checking sandbox backend...${NC}"

OS_NAME="$(uname -s)"
HAS_SANDBOX=false
HAS_NONO=false
command -v agent-sandbox >/dev/null 2>&1 && HAS_SANDBOX=true
command -v nono >/dev/null 2>&1 && HAS_NONO=true

if [ "$OS_NAME" = "Darwin" ]; then
    if [ "$HAS_NONO" = true ]; then
        echo -e "${GREEN}  ✓ macOS: nono detected as sandbox backend${NC}"
    else
        echo -e "${YELLOW}  ⚠ macOS: no sandbox backend found.${NC}"
        echo -e "${YELLOW}    agent-sandbox is Linux-only. Install nono:${NC}"
        echo "    brew install nono"
        echo "    See: https://github.com/always-further/nono"
    fi
else
    if [ "$HAS_SANDBOX" = true ]; then
        echo -e "${GREEN}  ✓ agent-sandbox detected${NC}"
    fi
    if [ "$HAS_NONO" = true ]; then
        echo -e "${GREEN}  ✓ nono detected (alternative backend)${NC}"
    fi
    if [ "$HAS_SANDBOX" = false ] && [ "$HAS_NONO" = false ]; then
        echo -e "${YELLOW}  ⚠ No sandbox backend found. Install one:${NC}"
        echo "    agent-sandbox: cd ../sandbox && ./install.sh"
        echo "    nono:          cargo install nono-cli"
    fi
fi
echo ""

# ── Summary ───────────────────────────────────────────────────────────
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Installation Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}Installed:${NC}"
echo "  Plugin:   $WASM_DST"
echo "  Layouts:  $LAYOUT_DIR/dashboard.kdl"
echo "  Config:   $CONFIG_DST"
echo "  Hooks:    ~/.local/bin/claude-status-hook.sh"
echo "            ~/.local/bin/codex-status-hook.sh"
echo "  Wrapper:  ~/.local/bin/lince-agent-wrapper"
echo "  Defaults: ~/.config/lince-dashboard/agents-defaults.toml"
echo "  Skill:    ~/.claude/skills/lince-setup/"
echo ""
echo -e "${GREEN}Sandbox backend:${NC}"
if [ "$OS_NAME" = "Darwin" ]; then
    echo "  macOS — nono required (agent-sandbox is Linux-only)"
    [ "$HAS_NONO" = true ] && echo "  ✓ nono installed" || echo "  ✗ Install: brew install nono"
else
    echo "  Linux — agent-sandbox (recommended) or nono"
    [ "$HAS_SANDBOX" = true ] && echo "  ✓ agent-sandbox installed"
    [ "$HAS_NONO" = true ] && echo "  ✓ nono installed (alternative)"
fi
echo ""
echo -e "${GREEN}Usage:${NC}"
echo "  source ~/.bashrc   # reload aliases"
echo "  zd                 # launch dashboard layout"
echo ""
echo -e "${GREEN}Keybindings:${NC}"
echo "  n       Spawn new agent"
echo "  k       Kill selected agent"
echo "  f/Enter Focus (show) agent pane"
echo "  h/Esc   Hide focused agent pane"
echo "  j/Down  Select next agent"
echo "  Up      Select previous agent"
echo "  ]/[     Cycle focus between agents"
echo "  i       Input mode (type to agent)"
echo ""
