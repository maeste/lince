#!/usr/bin/env bash
#
# LINCE Quickstart Installer
#
# Interactive TUI installer for LINCE — sandbox + dashboard for AI coding agents.
#
# Usage:
#   ./quickstart.sh              # Interactive TUI
#   ./quickstart.sh --defaults   # Install with defaults (all agents, bwrap, sandbox)
#   ./quickstart.sh --help       # Show help
#
# Exit codes:
#   0 - Success
#   1 - Error
#   2 - Cancelled by user
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colors & formatting ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── State ────────────────────────────────────────────────────────────
INSTALL_SANDBOX=true
SANDBOX_BACKEND="bwrap"   # bwrap | nono | both
SELECTED_AGENTS=()
INSTALL_VOXCODE=false
USE_DEFAULTS=false

# Available agents: key|display_name|description
AGENTS=(
    "claude|Claude Code|Anthropic's AI coding agent"
    "codex|OpenAI Codex|OpenAI's coding agent (CLI)"
    "gemini|Google Gemini CLI|Google's AI coding agent"
    "opencode|OpenCode|Open-source coding agent"
)
# Track selection state (1=selected, 0=not)
AGENT_SELECTED=(1 1 0 0)  # claude and codex on by default

# ── Helpers ──────────────────────────────────────────────────────────
confirm() {
    local prompt="$1"
    read -p "$prompt (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}"
    echo "  ╦  ╦╔╗╔╔═╗╔═╗"
    echo "  ║  ║║║║║  ║╣ "
    echo "  ╩═╝╩╝╚╝╚═╝╚═╝"
    echo -e "${NC}"
    echo -e "  ${BOLD}Secure Multi-Agent Coding Workstation${NC}"
    echo -e "  ${DIM}https://lince.sh${NC}"
    echo ""
}

print_separator() {
    echo -e "${DIM}────────────────────────────────────────────────────${NC}"
}

# ── TUI: Sandbox mode selection ──────────────────────────────────────
select_sandbox_mode() {
    echo ""
    echo -e "${BOLD}Step 1: Sandbox mode${NC}"
    echo ""
    echo -e "  LINCE wraps your AI agents in a sandbox so they can code"
    echo -e "  freely without reaching your SSH keys, credentials, or"
    echo -e "  pushing to production."
    echo ""
    echo -e "  ${GREEN}1)${NC} ${BOLD}Sandboxed${NC} ${GREEN}(recommended)${NC}"
    echo -e "     ${DIM}Agents run inside an isolated environment${NC}"
    echo ""
    echo -e "  ${YELLOW}2)${NC} ${BOLD}Dashboard only${NC} ${YELLOW}(no sandbox)${NC}"
    echo -e "     ${DIM}Agents run directly on your system — no isolation${NC}"
    echo ""
    read -p "  Choice [1]: " -n 1 -r
    echo ""

    case "${REPLY:-1}" in
        2)
            # ── BIG WARNING ──────────────────────────────────
            echo ""
            echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
            echo -e "${RED}${BOLD}║                    ⚠  WARNING  ⚠                    ║${NC}"
            echo -e "${RED}${BOLD}╠══════════════════════════════════════════════════════╣${NC}"
            echo -e "${RED}${BOLD}║                                                      ║${NC}"
            echo -e "${RED}${BOLD}║  Without sandboxing, AI agents have FULL ACCESS to:   ║${NC}"
            echo -e "${RED}${BOLD}║                                                      ║${NC}"
            echo -e "${RED}${BOLD}║    • Your SSH keys and GPG keys                      ║${NC}"
            echo -e "${RED}${BOLD}║    • Cloud credentials (AWS, GCP, Azure)              ║${NC}"
            echo -e "${RED}${BOLD}║    • Git push to any remote                          ║${NC}"
            echo -e "${RED}${BOLD}║    • All files on your system                        ║${NC}"
            echo -e "${RED}${BOLD}║    • Running processes and network                   ║${NC}"
            echo -e "${RED}${BOLD}║                                                      ║${NC}"
            echo -e "${RED}${BOLD}║  A single hallucinated command could:                ║${NC}"
            echo -e "${RED}${BOLD}║    • Push untested code to production                ║${NC}"
            echo -e "${RED}${BOLD}║    • Delete or modify critical files                 ║${NC}"
            echo -e "${RED}${BOLD}║    • Leak credentials to third parties               ║${NC}"
            echo -e "${RED}${BOLD}║                                                      ║${NC}"
            echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "${RED}${BOLD}  Are you sure you want to proceed WITHOUT sandboxing?${NC}"
            read -p "  Type 'yes' to confirm (anything else cancels): " -r
            if [ "$REPLY" != "yes" ]; then
                echo ""
                echo -e "  ${GREEN}Good choice. Switching to sandboxed mode.${NC}"
                INSTALL_SANDBOX=true
                return
            fi
            # Second confirmation
            echo ""
            echo -e "${RED}  Final confirmation: you accept full responsibility for${NC}"
            echo -e "${RED}  any damage caused by unsandboxed agents.${NC}"
            read -p "  Type 'I understand' to proceed: " -r
            if [ "$REPLY" != "I understand" ]; then
                echo ""
                echo -e "  ${GREEN}Switching to sandboxed mode.${NC}"
                INSTALL_SANDBOX=true
                return
            fi
            INSTALL_SANDBOX=false
            echo ""
            echo -e "  ${YELLOW}Dashboard-only mode selected. No sandbox will be installed.${NC}"
            ;;
        *)
            INSTALL_SANDBOX=true
            ;;
    esac
}

# ── TUI: Sandbox backend selection ───────────────────────────────────
select_sandbox_backend() {
    if [ "$INSTALL_SANDBOX" = false ]; then
        return
    fi

    local OS_NAME
    OS_NAME="$(uname -s)"

    echo ""
    print_separator
    echo -e "${BOLD}Step 2: Sandbox backend${NC}"
    echo ""

    if [ "$OS_NAME" = "Darwin" ]; then
        echo -e "  macOS detected — using ${BOLD}nono${NC} (Seatbelt sandbox)."
        echo -e "  ${DIM}bubblewrap is Linux-only.${NC}"
        SANDBOX_BACKEND="nono"
        echo ""
        if ! command -v nono >/dev/null 2>&1; then
            echo -e "  ${YELLOW}nono not found.${NC} Install with: ${CYAN}brew install nono${NC}"
            echo ""
        fi
        return
    fi

    # Linux: offer choice
    local has_bwrap=false has_nono=false
    command -v bwrap >/dev/null 2>&1 && has_bwrap=true
    command -v nono >/dev/null 2>&1 && has_nono=true

    echo -e "  ${GREEN}1)${NC} ${BOLD}bubblewrap (bwrap)${NC} ${GREEN}— recommended for Linux${NC}"
    echo -e "     ${DIM}Same technology as Flatpak. Battle-tested, zero overhead.${NC}"
    if [ "$has_bwrap" = true ]; then
        echo -e "     ${GREEN}✓ installed${NC}"
    else
        echo -e "     ${YELLOW}✗ not installed${NC} — ${DIM}sudo dnf install bubblewrap${NC}"
    fi
    echo ""

    echo -e "  ${CYAN}2)${NC} ${BOLD}nono${NC} ${CYAN}— Landlock LSM (Linux) + Seatbelt (macOS)${NC}"
    echo -e "     ${DIM}Newer, supports both Linux and macOS. Uses kernel security modules.${NC}"
    if [ "$has_nono" = true ]; then
        echo -e "     ${GREEN}✓ installed${NC}"
    else
        echo -e "     ${YELLOW}✗ not installed${NC} — ${DIM}cargo install nono-cli${NC}"
    fi
    echo ""

    echo -e "  ${BLUE}3)${NC} ${BOLD}Both${NC}"
    echo -e "     ${DIM}Install support for both backends. Choose per-agent later.${NC}"
    echo ""

    read -p "  Choice [1]: " -n 1 -r
    echo ""

    case "${REPLY:-1}" in
        2) SANDBOX_BACKEND="nono" ;;
        3) SANDBOX_BACKEND="both" ;;
        *) SANDBOX_BACKEND="bwrap" ;;
    esac

    echo -e "  ${GREEN}✓${NC} Backend: ${BOLD}$SANDBOX_BACKEND${NC}"
}

# ── TUI: Agent selection ─────────────────────────────────────────────
select_agents() {
    echo ""
    print_separator
    echo -e "${BOLD}Step 3: Select agents to configure${NC}"
    echo ""
    echo -e "  ${DIM}These are sandboxing wrappers and dashboard entries for each agent.${NC}"
    echo -e "  ${DIM}The agents themselves (claude, codex, gemini, etc.) must be${NC}"
    echo -e "  ${DIM}installed separately — that is outside the scope of this installer.${NC}"
    echo ""
    echo -e "  ${DIM}Toggle with number keys, press Enter when done:${NC}"
    echo ""

    while true; do
        for i in "${!AGENTS[@]}"; do
            IFS='|' read -r key name desc <<< "${AGENTS[$i]}"
            if [ "${AGENT_SELECTED[$i]}" = "1" ]; then
                echo -e "  ${GREEN}[x]${NC} ${BOLD}$((i+1))) $name${NC} ${DIM}— $desc${NC}"
            else
                echo -e "  ${DIM}[ ] $((i+1))) $name — $desc${NC}"
            fi
        done
        echo ""
        echo -e "  ${DIM}Press 1-${#AGENTS[@]} to toggle, Enter to confirm, 'a' for all, 'n' for none${NC}"
        read -p "  > " -n 1 -r
        echo ""

        case "$REPLY" in
            [1-9])
                local idx=$((REPLY - 1))
                if [ $idx -lt ${#AGENTS[@]} ]; then
                    if [ "${AGENT_SELECTED[$idx]}" = "1" ]; then
                        AGENT_SELECTED[$idx]=0
                    else
                        AGENT_SELECTED[$idx]=1
                    fi
                fi
                ;;
            a|A)
                for i in "${!AGENTS[@]}"; do AGENT_SELECTED[$i]=1; done
                ;;
            n|N)
                for i in "${!AGENTS[@]}"; do AGENT_SELECTED[$i]=0; done
                ;;
            "")
                # Enter pressed — confirm selection
                break
                ;;
        esac

        # Move cursor up to redraw (number of agents + 2 lines for prompt)
        local lines_up=$(( ${#AGENTS[@]} + 3 ))
        echo -en "\033[${lines_up}A\033[J"
    done

    # Build selected agents list
    SELECTED_AGENTS=()
    for i in "${!AGENTS[@]}"; do
        if [ "${AGENT_SELECTED[$i]}" = "1" ]; then
            IFS='|' read -r key _ _ <<< "${AGENTS[$i]}"
            SELECTED_AGENTS+=("$key")
        fi
    done

    if [ ${#SELECTED_AGENTS[@]} -eq 0 ]; then
        echo -e "  ${YELLOW}No agents selected. The dashboard will be installed${NC}"
        echo -e "  ${YELLOW}but no agent types will be pre-configured.${NC}"
        echo -e "  ${DIM}You can add agents later via /lince-setup or config.toml.${NC}"
    else
        echo -e "  ${GREEN}✓${NC} Selected: ${BOLD}${SELECTED_AGENTS[*]}${NC}"
    fi
}

# ── TUI: VoxCode (voice input) ───────────────────────────────────────
select_voxcode() {
    echo ""
    print_separator
    echo -e "${BOLD}Step 4: Voice input (VoxCode)${NC}"
    echo ""
    echo -e "  VoxCode lets you speak to your agents — transcriptions are"
    echo -e "  routed to the focused agent via the dashboard."
    echo -e "  All audio processing happens locally (Whisper)."
    echo ""
    echo -e "  ${DIM}Requires: microphone, ~1GB disk (Whisper model), GPU recommended${NC}"
    echo -e "  ${DIM}Installed from: https://github.com/RisorseArtificiali/voxcode${NC}"
    echo ""

    if command -v voxcode >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓ VoxCode already installed${NC}"
        INSTALL_VOXCODE=false
        return
    fi

    echo -e "  ${GREEN}1)${NC} ${BOLD}Yes${NC} — install VoxCode (voice input)"
    echo -e "  ${DIM}2)${NC} No  — skip for now (can install later)"
    echo ""
    read -p "  Choice [2]: " -n 1 -r
    echo ""

    case "${REPLY:-2}" in
        1|y|Y)
            # Check uv
            if ! command -v uv >/dev/null 2>&1; then
                echo ""
                echo -e "  ${YELLOW}VoxCode requires 'uv' (Python package manager).${NC}"
                echo -e "  ${DIM}Install with: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
                echo ""
                if confirm "  Install uv now?"; then
                    curl -LsSf https://astral.sh/uv/install.sh | sh
                    export PATH="$HOME/.local/bin:$PATH"
                    if command -v uv >/dev/null 2>&1; then
                        echo -e "  ${GREEN}✓ uv installed${NC}"
                    else
                        echo -e "  ${RED}✗ uv installation failed. Skipping VoxCode.${NC}"
                        INSTALL_VOXCODE=false
                        return
                    fi
                else
                    echo -e "  ${YELLOW}Skipping VoxCode (uv required).${NC}"
                    INSTALL_VOXCODE=false
                    return
                fi
            fi
            INSTALL_VOXCODE=true
            echo -e "  ${GREEN}✓${NC} VoxCode will be installed"
            ;;
        *)
            INSTALL_VOXCODE=false
            echo -e "  ${DIM}Skipped. Install later: https://github.com/RisorseArtificiali/voxcode${NC}"
            ;;
    esac
}

# ── TUI: Summary and confirm ────────────────────────────────────────
confirm_installation() {
    echo ""
    print_separator
    echo -e "${BOLD}Installation summary${NC}"
    echo ""

    if [ "$INSTALL_SANDBOX" = true ]; then
        echo -e "  ${GREEN}✓${NC} agent-sandbox    ${DIM}(secure isolation for agents)${NC}"
        echo -e "    Backend: ${BOLD}$SANDBOX_BACKEND${NC}"
    else
        echo -e "  ${RED}✗${NC} agent-sandbox    ${DIM}(SKIPPED — no sandboxing)${NC}"
    fi

    echo -e "  ${GREEN}✓${NC} lince-dashboard  ${DIM}(multi-agent TUI)${NC}"

    if [ "$INSTALL_VOXCODE" = true ]; then
        echo -e "  ${GREEN}✓${NC} voxcode          ${DIM}(voice input via Whisper)${NC}"
    fi

    echo ""
    echo -e "  Agents:"
    for i in "${!AGENTS[@]}"; do
        IFS='|' read -r key name _ <<< "${AGENTS[$i]}"
        if [ "${AGENT_SELECTED[$i]}" = "1" ]; then
            if [ "$INSTALL_SANDBOX" = true ]; then
                case "$SANDBOX_BACKEND" in
                    bwrap) echo -e "    ${GREEN}✓${NC} $name ${DIM}(sandboxed via bwrap)${NC}" ;;
                    nono)  echo -e "    ${GREEN}✓${NC} $name ${DIM}(sandboxed via nono)${NC}" ;;
                    both)  echo -e "    ${GREEN}✓${NC} $name ${DIM}(bwrap + nono variants)${NC}" ;;
                esac
            else
                echo -e "    ${YELLOW}!${NC} $name ${DIM}(unsandboxed)${NC}"
            fi
        fi
    done

    echo ""
    if ! confirm "  Proceed with installation?"; then
        echo "  Cancelled."
        exit 2
    fi
}

# ── Generate filtered agents-defaults.toml ───────────────────────────
generate_agent_defaults() {
    local src="$SCRIPT_DIR/lince-dashboard/agents-defaults.toml"
    local dst="$1"

    if [ ! -f "$src" ]; then
        echo -e "  ${YELLOW}⚠ agents-defaults.toml not found — using empty config${NC}"
        echo "# No agent types configured. Add agents via /lince-setup or edit this file." > "$dst"
        return
    fi

    # Start with header
    head -13 "$src" > "$dst"

    for agent in "${SELECTED_AGENTS[@]}"; do
        echo "" >> "$dst"

        if [ "$INSTALL_SANDBOX" = true ]; then
            # Add sandboxed variant(s)
            case "$SANDBOX_BACKEND" in
                bwrap)
                    # Claude uses base "claude" (already bwrap), others use "<agent>-bwrap"
                    if [ "$agent" = "claude" ]; then
                        extract_agent_block "$src" "agents.claude" >> "$dst"
                    else
                        extract_agent_block "$src" "agents.${agent}-bwrap" >> "$dst"
                        # If bwrap block doesn't exist, fall back to base
                        if ! grep -q "\[agents\.${agent}-bwrap\]" "$src"; then
                            extract_agent_block "$src" "agents.${agent}" >> "$dst"
                        fi
                    fi
                    ;;
                nono)
                    extract_agent_block "$src" "agents.${agent}-nono" >> "$dst"
                    # If nono block doesn't exist, fall back to base
                    if ! grep -q "\[agents\.${agent}-nono\]" "$src"; then
                        extract_agent_block "$src" "agents.${agent}" >> "$dst"
                    fi
                    ;;
                both)
                    # Include bwrap variant
                    if [ "$agent" = "claude" ]; then
                        extract_agent_block "$src" "agents.claude" >> "$dst"
                    else
                        extract_agent_block "$src" "agents.${agent}-bwrap" >> "$dst"
                        if ! grep -q "\[agents\.${agent}-bwrap\]" "$src"; then
                            extract_agent_block "$src" "agents.${agent}" >> "$dst"
                        fi
                    fi
                    # Include nono variant
                    extract_agent_block "$src" "agents.${agent}-nono" >> "$dst"
                    ;;
            esac
        else
            # Unsandboxed: use base agent or unsandboxed variant
            if [ "$agent" = "claude" ]; then
                extract_agent_block "$src" "agents.claude-unsandboxed" >> "$dst"
            else
                extract_agent_block "$src" "agents.${agent}" >> "$dst"
            fi
        fi
    done
}

# Extract a TOML block from [agents.X] to the next [agents.Y] or EOF
extract_agent_block() {
    local file="$1"
    local section="$2"

    # Use awk to extract from [section] to next [agents.*] or EOF
    # Also captures sub-tables like [agents.codex.env_vars]
    awk -v sec="[$section]" '
        BEGIN { printing=0 }
        /^\[agents\./ {
            if ($0 == sec || (printing && index($0, sec ".") == 1)) {
                printing=1
            } else if (printing) {
                printing=0
            }
        }
        printing { print }
    ' "$file"
}

# ── Install VoxCode ──────────────────────────────────────────────────
do_install_voxcode() {
    if [ "$INSTALL_VOXCODE" = false ]; then
        return
    fi

    echo ""
    print_separator
    echo -e "${BOLD}Installing VoxCode (voice input)...${NC}"
    echo ""

    local VOXCODE_DIR="$HOME/.local/share/voxcode"

    if [ -d "$VOXCODE_DIR" ]; then
        echo -e "  ${DIM}Updating existing clone...${NC}"
        cd "$VOXCODE_DIR" && git pull --ff-only 2>/dev/null || true
    else
        echo -e "  ${DIM}Cloning voxcode...${NC}"
        git clone https://github.com/RisorseArtificiali/voxcode.git "$VOXCODE_DIR"
    fi

    cd "$VOXCODE_DIR"
    if bash install.sh; then
        echo -e "${GREEN}✓ VoxCode installed${NC}"
    else
        echo -e "${RED}✗ VoxCode installation failed${NC}"
        echo -e "  ${DIM}Dashboard will use the standard layout (no voice pane).${NC}"
    fi
}

# ── Install sandbox ─────────────────────────────────────────────────
do_install_sandbox() {
    if [ "$INSTALL_SANDBOX" = false ]; then
        return
    fi

    echo ""
    print_separator
    echo -e "${BOLD}Installing agent-sandbox...${NC}"
    echo ""

    cd "$SCRIPT_DIR/sandbox"
    if bash install.sh; then
        echo -e "${GREEN}✓ agent-sandbox installed${NC}"
    else
        echo -e "${RED}✗ agent-sandbox installation failed${NC}"
        if ! confirm "Continue anyway?"; then exit 1; fi
    fi
}

# ── Install dashboard ───────────────────────────────────────────────
do_install_dashboard() {
    echo ""
    print_separator
    echo -e "${BOLD}Installing lince-dashboard...${NC}"
    echo ""

    cd "$SCRIPT_DIR/lince-dashboard"
    if bash install.sh; then
        echo -e "${GREEN}✓ lince-dashboard installed${NC}"
    else
        echo -e "${RED}✗ lince-dashboard installation failed${NC}"
        if ! confirm "Continue anyway?"; then exit 1; fi
    fi

    # Overwrite agents-defaults.toml with filtered version
    local defaults_dst="$HOME/.config/lince-dashboard/agents-defaults.toml"
    if [ ${#SELECTED_AGENTS[@]} -gt 0 ]; then
        echo ""
        echo -e "${CYAN}Configuring selected agents...${NC}"
        generate_agent_defaults "$defaults_dst"
        echo -e "${GREEN}✓ Agent defaults written: $defaults_dst${NC}"
        echo -e "  ${DIM}Configured: ${SELECTED_AGENTS[*]}${NC}"
    fi
}

# ── Check prerequisites ─────────────────────────────────────────────
check_prerequisites() {
    echo -e "${BOLD}Checking prerequisites...${NC}"
    echo ""

    local warnings=()

    # Python
    if command -v python3 >/dev/null 2>&1; then
        local pyver
        pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "  ${GREEN}✓${NC} Python $pyver"
    else
        warnings+=("Python 3.11+ not found")
        echo -e "  ${YELLOW}✗${NC} Python 3.11+ not found"
    fi

    # Git
    if command -v git >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} git"
    else
        warnings+=("git not found")
        echo -e "  ${RED}✗${NC} git not found"
    fi

    # Zellij
    if command -v zellij >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} zellij $(zellij --version 2>/dev/null | awk '{print $2}')"
    else
        warnings+=("zellij not found (required for dashboard)")
        echo -e "  ${YELLOW}✗${NC} zellij not found — needed for dashboard"
    fi

    # Rust (for WASM build)
    if command -v rustc >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} rustc $(rustc --version 2>/dev/null | awk '{print $2}')"
    else
        warnings+=("Rust not found (required to build dashboard plugin)")
        echo -e "  ${YELLOW}✗${NC} rustc not found — needed to build dashboard"
    fi

    # Sandbox backends
    if [ "$INSTALL_SANDBOX" = true ]; then
        case "$SANDBOX_BACKEND" in
            bwrap|both)
                if command -v bwrap >/dev/null 2>&1; then
                    echo -e "  ${GREEN}✓${NC} bubblewrap"
                else
                    warnings+=("bubblewrap not found")
                    echo -e "  ${YELLOW}✗${NC} bubblewrap — ${DIM}sudo dnf install bubblewrap${NC}"
                fi
                ;;&
            nono|both)
                if command -v nono >/dev/null 2>&1; then
                    echo -e "  ${GREEN}✓${NC} nono"
                else
                    warnings+=("nono not found")
                    echo -e "  ${YELLOW}✗${NC} nono — ${DIM}cargo install nono-cli${NC}"
                fi
                ;;
        esac
    fi

    if [ ${#warnings[@]} -gt 0 ]; then
        echo ""
        echo -e "  ${YELLOW}${#warnings[@]} warning(s). Install missing tools for full functionality.${NC}"
        if ! confirm "  Continue with installation?"; then
            exit 2
        fi
    fi
}

# ── Summary ──────────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${BLUE}${BOLD}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}  Installation Complete${NC}"
    echo -e "${BLUE}${BOLD}════════════════════════════════════════════════════${NC}"
    echo ""

    if [ "$INSTALL_SANDBOX" = true ]; then
        echo -e "  ${GREEN}✓${NC} agent-sandbox (${SANDBOX_BACKEND})"
    fi
    echo -e "  ${GREEN}✓${NC} lince-dashboard"
    if command -v voxcode >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} voxcode (voice input)"
    fi

    if [ ${#SELECTED_AGENTS[@]} -gt 0 ]; then
        echo ""
        echo -e "  Configured agents:"
        for agent in "${SELECTED_AGENTS[@]}"; do
            for entry in "${AGENTS[@]}"; do
                IFS='|' read -r key name _ <<< "$entry"
                if [ "$key" = "$agent" ]; then
                    if [ "$INSTALL_SANDBOX" = true ]; then
                        echo -e "    ${GREEN}✓${NC} $name (sandboxed)"
                    else
                        echo -e "    ${YELLOW}!${NC} $name (unsandboxed)"
                    fi
                    break
                fi
            done
        done
    fi

    echo ""
    echo -e "  ${BOLD}Get started:${NC}"
    echo ""
    echo -e "    ${CYAN}source ~/.bashrc${NC}"
    echo -e "    ${CYAN}zd${NC}"
    echo ""
    echo -e "  ${DIM}Press 'n' in the dashboard to spawn an agent.${NC}"
    echo -e "  ${DIM}Press '?' for the full keybindings help.${NC}"

    if ! command -v voxcode >/dev/null 2>&1; then
        echo ""
        echo -e "  ${YELLOW}Optional — Voice input:${NC}"
        echo -e "  ${DIM}https://github.com/RisorseArtificiali/voxcode${NC}"
    fi
    echo ""
}

# ── Parse arguments ──────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --defaults)
            USE_DEFAULTS=true
            shift
            ;;
        --help|-h)
            echo "LINCE Quickstart Installer"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --defaults   Install with defaults (all agents, bwrap sandbox)"
            echo "  --help       Show this help"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# ── Main ─────────────────────────────────────────────────────────────
print_banner

if [ "$USE_DEFAULTS" = true ]; then
    INSTALL_SANDBOX=true
    SANDBOX_BACKEND="bwrap"
    for i in "${!AGENTS[@]}"; do AGENT_SELECTED[$i]=1; done
    SELECTED_AGENTS=()
    for i in "${!AGENTS[@]}"; do
        IFS='|' read -r key _ _ <<< "${AGENTS[$i]}"
        SELECTED_AGENTS+=("$key")
    done
    echo -e "  ${DIM}Using defaults: all agents, bwrap sandbox${NC}"
else
    select_sandbox_mode
    select_sandbox_backend
    select_agents
    select_voxcode
    confirm_installation
fi

print_separator
check_prerequisites
print_separator

do_install_sandbox
do_install_voxcode    # before dashboard so step 12 detects voxcode
do_install_dashboard
print_summary
