#!/usr/bin/env bash
#
# LINCE Quickstart Installer
# 
# Interactive installer for LINCE modules. Can be run in three modes:
#   - Interactive: ./quickstart.sh (shows menu)
#   - Mini:        ./quickstart.sh --mini (sandbox + dashboard)
#   - Full:        ./quickstart.sh --full (same as mini — voice modules are separate repos)
#   - Non-interactive: Add --yes to auto-confirm prompts
#
# Exit codes:
#   0 - Success
#   1 - Error (missing prerequisites, etc.)
#   2 - Cancelled by user
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES=("sandbox" "lince-dashboard")

# Options
AUTO_YES=false
MODE="interactive"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mini)
            MODE="mini"
            shift
            ;;
        --full)
            MODE="full"
            shift
            ;;
        --yes)
            AUTO_YES=true
            shift
            ;;
        --help|-h)
            echo "LINCE Quickstart Installer"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --mini     Install sandbox + lince-dashboard only"
            echo "  --full     Install all modules"
            echo "  --yes      Auto-confirm all prompts"
            echo "  --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0              # Interactive menu"
            echo "  $0 --mini       # Mini install (non-interactive)"
            echo "  $0 --full --yes  # Full install (non-interactive)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
confirm() {
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Banner
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   LINCE Quickstart Installer${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check prerequisites
log_step "Checking prerequisites..."

MISSING_PREREQ=()

if ! command -v bash >/dev/null 2>&1; then
    MISSING_PREREQ+=("bash")
fi

if [ ${#MISSING_PREREQ[@]} -gt 0 ]; then
    log_error "Missing prerequisites:"
    for prereq in "${MISSING_PREREQ[@]}"; do
        echo "  - $prereq"
    done
    exit 1
fi

log_info "Found: bash"
echo ""

# Determine which modules to install based on mode
case $MODE in
    mini)
        MODULES_TO_INSTALL=("sandbox" "lince-dashboard")
        ;;
    full)
        MODULES_TO_INSTALL=("${MODULES[@]}")
        ;;
    interactive)
        # Show menu
        echo "Select your setup:"
        echo ""
        echo "  1) Install  (sandbox + lince-dashboard)"
        echo "  2) Exit"
        echo ""
        
        read -p "Choice: " -n 1 -r CHOICE
        echo ""
        
        case $CHOICE in
            1)
                MODULES_TO_INSTALL=("sandbox" "lince-dashboard")
                ;;
            2|*)
                echo "Exiting."
                exit 0
                ;;
        esac
        ;;
esac

echo ""
log_info "Installing: ${MODULES_TO_INSTALL[*]}"
echo ""

# Check dependencies for selected modules
log_step "Checking module dependencies..."

check_prerequisite() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log_warn "Missing: $1 (required for $2)"
        if confirm "Continue anyway?"; then
            return 1
        else
            exit 2
        fi
    fi
    return 0
}

# Sandbox has no module dependencies
# lince-dashboard requires: zellij, rust (for WASM)
if [[ " ${MODULES_TO_INSTALL[*]} " =~ " lince-dashboard " ]]; then
    check_prerequisite "zellij" "lince-dashboard" || true
fi


echo ""

# Install modules in order (respecting dependencies)
# Order: sandbox -> lince-dashboard

INSTALL_ORDER=(
    "sandbox:sandbox/install.sh"
    "lince-dashboard:lince-dashboard/install.sh"
)

TOTAL=${#MODULES_TO_INSTALL[@]}
CURRENT=0

for module in "${MODULES_TO_INSTALL[@]}"; do
    CURRENT=$((CURRENT + 1))
    
    # Find install script
    SCRIPT_PATH=""
    for entry in "${INSTALL_ORDER[@]}"; do
        key="${entry%%:*}"
        value="${entry##*:}"
        if [ "$key" = "$module" ]; then
            SCRIPT_PATH="$SCRIPT_DIR/$value"
            break
        fi
    done
    
    if [ -z "$SCRIPT_PATH" ] || [ ! -f "$SCRIPT_PATH" ]; then
        log_warn "No install script for $module, skipping"
        continue
    fi
    
    echo -e "${BLUE}--- Installing $module ($CURRENT/$TOTAL) ---${NC}"
    
    if bash "$SCRIPT_PATH"; then
        log_info "$module installed successfully"
    else
        log_error "Failed to install $module"
        if ! confirm "Continue with remaining modules?"; then
            exit 1
        fi
    fi
    echo ""
done

# Final verification
log_step "Verifying installation..."

INSTALLED=()

if [[ " ${MODULES_TO_INSTALL[*]} " =~ " sandbox " ]]; then
    if command -v agent-sandbox >/dev/null 2>&1; then
        INSTALLED+=("agent-sandbox")
    fi
fi

if [[ " ${MODULES_TO_INSTALL[*]} " =~ " lince-dashboard " ]]; then
    if [ -f "$HOME/.config/zellij/plugins/lince-dashboard.wasm" ]; then
        INSTALLED+=("lince-dashboard")
    fi
fi


# Summary
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Installation Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}Installed modules:${NC}"
for mod in "${INSTALLED[@]}"; do
    echo "  - $mod"
done
echo ""

# Usage instructions
echo -e "${GREEN}Usage:${NC}"
echo ""

if [[ " ${MODULES_TO_INSTALL[*]} " =~ " lince-dashboard " ]]; then
    echo "  # Start the dashboard:"
    echo "  source ~/.bashrc"
    echo "  zd"
    echo ""
fi

echo -e "${YELLOW}Optional — Voice input:${NC}"
echo "  Install VoxCode for voice-controlled coding:"
echo "  https://github.com/RisorseArtificiali/voxcode"
echo ""
echo -e "${YELLOW}For detailed documentation, see:${NC}"
echo "  - README.md (main docs)"
echo "  - QUICKSTART.md (step-by-step guide)"
echo ""
