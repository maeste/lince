#!/usr/bin/env bash
# claude-status-hook.sh — Claude Code hook that reports agent status
# to the lince-dashboard Zellij plugin via pipe (primary) and file (fallback).
#
# Emits a minimal JSON contract: {"agent_id": "<id>", "event": "<native_name>"}
# Native event names are passed through verbatim — the dashboard's per-agent
# event_map (in agents-defaults.toml) maps them to canonical status values
# (running / input / permission / stopped). See LINCE-118 / LINCE-122.
#
# Claude Code pipes JSON to stdin with at least: hook_event_name.
# For Notification events the dashboard cares about notification_type
# (idle_prompt / permission_prompt) — we forward that as the native event.
#
# Environment:
#   LINCE_AGENT_ID   — set by the dashboard when spawning the agent
#   ZELLIJ           — set by Zellij when running inside a session
#   LINCE_STATUS_DIR — override for status file directory (default: /tmp/lince-dashboard)

set -euo pipefail

AGENT_ID="${LINCE_AGENT_ID:-}"
STATUS_DIR="${LINCE_STATUS_DIR:-/tmp/lince-dashboard}"
LOG_FILE="/tmp/lince-dashboard/hook-debug.log"

mkdir -p /tmp/lince-dashboard 2>/dev/null || true

if [ -z "$AGENT_ID" ]; then
    exit 0
fi

INPUT=""
if [ ! -t 0 ]; then
    INPUT=$(cat)
fi

HAS_JQ=false
command -v jq >/dev/null 2>&1 && HAS_JQ=true

extract_json_field() {
    local field="$1"
    if $HAS_JQ && [ -n "$INPUT" ]; then
        local val
        val=$(echo "$INPUT" | jq -r ".$field // empty" 2>/dev/null || true)
        if [ -n "$val" ]; then echo "$val"; return; fi
    fi
    if [ -n "$INPUT" ] && [[ "$INPUT" =~ \"${field}\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
}

HOOK_EVENT=$(extract_json_field "hook_event_name")
if [ -z "$HOOK_EVENT" ]; then
    exit 0
fi

# For Notification events, the meaningful native name is the notification_type
# (idle_prompt / permission_prompt). Everything else is forwarded verbatim.
NATIVE_EVENT="$HOOK_EVENT"
if [ "$HOOK_EVENT" = "Notification" ]; then
    NOTIF_TYPE=$(extract_json_field "notification_type")
    if [ -n "$NOTIF_TYPE" ]; then
        NATIVE_EVENT="$NOTIF_TYPE"
    fi
fi

PAYLOAD="{\"agent_id\":\"${AGENT_ID}\",\"event\":\"${NATIVE_EVENT}\"}"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ${AGENT_ID} ${NATIVE_EVENT}" >> "$LOG_FILE" 2>/dev/null || true

# Primary: send via zellij pipe (if inside a Zellij session)
if [ -n "${ZELLIJ:-}" ] && command -v zellij >/dev/null 2>&1; then
    echo "$PAYLOAD" | timeout 2 zellij pipe --name "claude-status" >/dev/null 2>&1 || true
fi

# Fallback: write status to file (always, as backup)
mkdir -p "${STATUS_DIR}" 2>/dev/null || true
echo "$NATIVE_EVENT" > "${STATUS_DIR}/claude-${AGENT_ID}.state" 2>/dev/null || true

exit 0
