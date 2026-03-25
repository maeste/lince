#!/usr/bin/env bash
# validate-agent.sh -- Validate agent registration with agent-sandbox
# Usage: validate-agent.sh <agent-key>

set -euo pipefail

KEY="${1:?Usage: validate-agent.sh <agent-key>}"

echo "Validating agent '$KEY'..."
echo ""

# Check sandbox config exists
SANDBOX_CONFIG="$HOME/.agent-sandbox/config.toml"
if [ ! -f "$SANDBOX_CONFIG" ]; then
    echo "  ERROR: Sandbox config not found at $SANDBOX_CONFIG"
    exit 1
fi

# Check agent section exists in sandbox config
if grep -q "\\[agents\\.$KEY\\]" "$SANDBOX_CONFIG" 2>/dev/null; then
    echo "  Sandbox config: [agents.$KEY] section found"
else
    echo "  WARNING: [agents.$KEY] section NOT found in $SANDBOX_CONFIG"
fi

# Check binary
BINARY=$(grep -A1 "\\[agents\\.$KEY\\]" "$SANDBOX_CONFIG" 2>/dev/null | grep "command" | sed 's/.*= *"\(.*\)"/\1/' || echo "")
if [ -n "$BINARY" ]; then
    if command -v "$BINARY" >/dev/null 2>&1; then
        echo "  Binary '$BINARY': found at $(which "$BINARY")"
    else
        echo "  Binary '$BINARY': NOT FOUND in PATH"
    fi
else
    echo "  WARNING: Could not extract binary name from config"
fi

# Check dashboard defaults
DEFAULTS_FILE="$HOME/.agent-sandbox/agents-defaults.toml"
if [ -f "$DEFAULTS_FILE" ]; then
    if grep -q "\\[$KEY\\]" "$DEFAULTS_FILE" 2>/dev/null; then
        echo "  Dashboard config: [$KEY] section found"
    else
        echo "  WARNING: [$KEY] section NOT found in $DEFAULTS_FILE"
    fi
else
    echo "  WARNING: Dashboard defaults not found at $DEFAULTS_FILE"
fi

# Dry run
echo ""
echo "Dry run:"
if command -v agent-sandbox >/dev/null 2>&1; then
    agent-sandbox run -a "$KEY" -p /tmp/test --dry-run 2>&1 || echo "  Dry run failed -- check config"
else
    echo "  SKIPPED: agent-sandbox not found in PATH"
fi
