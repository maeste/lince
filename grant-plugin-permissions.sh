#!/usr/bin/env bash
#
# Pre-grant Zellij permissions for the lince-dashboard plugin.
#
# Zellij stores granted permissions in ~/.cache/zellij/permissions.kdl.
# On a fresh install, the plugin shows a permission dialog that the user must
# accept. If the dialog is missed or doesn't appear, the plugin runs without
# permissions and panics on any privileged API call.
#
# This script creates the permissions.kdl cache file so the plugin starts
# with all required permissions already granted.
#
# Usage:
#   bash grant-plugin-permissions.sh           # grant permissions
#   bash grant-plugin-permissions.sh --show    # show current permissions
#   bash grant-plugin-permissions.sh --reset   # remove cached permissions
#

set -e

CACHE_DIR="$HOME/.cache/zellij"
PERMS_FILE="$CACHE_DIR/permissions.kdl"
PLUGIN_WASM="$HOME/.config/zellij/plugins/lince-dashboard.wasm"

show_permissions() {
    if [ -f "$PERMS_FILE" ]; then
        echo "Current permissions cache ($PERMS_FILE):"
        echo ""
        cat "$PERMS_FILE"
    else
        echo "No permissions cache found at $PERMS_FILE"
    fi
}

reset_permissions() {
    if [ -f "$PERMS_FILE" ]; then
        rm "$PERMS_FILE"
        echo "Removed $PERMS_FILE"
    else
        echo "No permissions cache to remove"
    fi
}

grant_permissions() {
    mkdir -p "$CACHE_DIR"

    # If permissions.kdl already exists and contains our plugin, skip
    if [ -f "$PERMS_FILE" ] && grep -q "lince-dashboard.wasm" "$PERMS_FILE" 2>/dev/null; then
        echo "Permissions already granted for lince-dashboard plugin."
        return 0
    fi

    # Append to existing file (preserve permissions for other plugins)
    cat >> "$PERMS_FILE" << EOF
"${PLUGIN_WASM}" {
    RunCommands
    ReadApplicationState
    ReadCliPipes
    WriteToStdin
    ChangeApplicationState
    OpenTerminalsOrPlugins
    MessageAndLaunchOtherPlugins
}
EOF

    echo "Permissions granted for lince-dashboard plugin."
    echo "Written to: $PERMS_FILE"
}

case "${1:-}" in
    --show)   show_permissions ;;
    --reset)  reset_permissions ;;
    --help|-h)
        echo "Usage: $0 [--show|--reset|--help]"
        echo "  (no args)  Grant permissions for lince-dashboard plugin"
        echo "  --show     Show current permissions cache"
        echo "  --reset    Remove cached permissions"
        ;;
    *)        grant_permissions ;;
esac
