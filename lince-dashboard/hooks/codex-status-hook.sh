#!/usr/bin/env bash
# codex-status-hook.sh — Codex notify hook that reports turn-complete/idle
# status to the lince-dashboard Zellij plugin via pipe (primary) and file (fallback).
#
# Codex notify runs an external program and appends a JSON payload as an argv item.
# Some integrations may prefer stdin, so this script supports both.
#
# Environment:
#   LINCE_AGENT_ID   — set by the dashboard when spawning the agent
#   ZELLIJ           — set by Zellij when running inside a session
#   LINCE_STATUS_DIR — override for status file directory (default: /tmp/lince-dashboard)

set -euo pipefail

AGENT_ID="${LINCE_AGENT_ID:-}"
STATUS_DIR="${LINCE_STATUS_DIR:-/tmp/lince-dashboard}"
LOG_FILE="/tmp/lince-dashboard/codex-hook-debug.log"

mkdir -p /tmp/lince-dashboard 2>/dev/null || true

{
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    echo "  AGENT_ID=${AGENT_ID:-<empty>}"
    echo "  ZELLIJ=${ZELLIJ:-<not set>}"
    echo "  ZELLIJ_SESSION=${ZELLIJ_SESSION_NAME:-<not set>}"
    echo "  PWD=$PWD"
    echo "  PATH_has_zellij=$(command -v zellij 2>/dev/null || echo 'NO')"
} >> "$LOG_FILE" 2>/dev/null || true

if [ -z "$AGENT_ID" ]; then
    echo "  EXIT: no AGENT_ID" >> "$LOG_FILE" 2>/dev/null || true
    exit 0
fi

INPUT="${1:-}"
if [ -z "$INPUT" ] && [ ! -t 0 ]; then
    INPUT=$(cat)
fi

HAS_JQ=false
command -v jq >/dev/null 2>&1 && HAS_JQ=true

extract_json_field() {
    local field="$1"
    if $HAS_JQ && [ -n "$INPUT" ]; then
        local val
        val=$(printf '%s' "$INPUT" | jq -r --arg field "$field" '.[$field] // empty' 2>/dev/null || true)
        if [ -n "$val" ]; then
            echo "$val"
            return
        fi
    fi
    if [ -n "$INPUT" ]; then
        if [[ "$INPUT" =~ \"${field}\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
            echo "${BASH_REMATCH[1]}"
            return
        fi
    fi
}

EVENT_TYPE=$(extract_json_field "type")
MODEL=$(extract_json_field "model")
LAST_MESSAGE=$(extract_json_field "last-assistant-message")

# Codex notify currently fires on turn completion, so the dashboard state should
# become idle once this hook runs. Unknown payloads are still treated as idle.
STATUS="idle"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "")

if $HAS_JQ; then
    PAYLOAD=$(jq -nc \
        --arg id "$AGENT_ID" \
        --arg event "$STATUS" \
        --arg ts "$TIMESTAMP" \
        --arg notify_type "${EVENT_TYPE:-}" \
        --arg model "${MODEL:-}" \
        --arg message "${LAST_MESSAGE:-}" \
        '{agent_id: $id, event: $event, timestamp: $ts}
         + (if $notify_type != "" then {notify_type: $notify_type} else {} end)
         + (if $model != "" then {model: $model} else {} end)
         + (if $message != "" then {last_message: $message} else {} end)')
else
    PAYLOAD="{\"agent_id\":\"${AGENT_ID}\",\"event\":\"${STATUS}\",\"timestamp\":\"${TIMESTAMP}\"}"
fi

echo "  EVENT_TYPE=${EVENT_TYPE:-<empty>} STATUS=$STATUS PAYLOAD=$PAYLOAD" >> "$LOG_FILE" 2>/dev/null || true

if [ -n "${ZELLIJ:-}" ] && command -v zellij >/dev/null 2>&1; then
    PIPE_OUT=$(printf '%s' "$PAYLOAD" | timeout 2 zellij pipe --name "lince-status" 2>&1) && \
        echo "  PIPE: ok" >> "$LOG_FILE" || \
        echo "  PIPE: failed ($PIPE_OUT)" >> "$LOG_FILE" 2>/dev/null || true
else
    echo "  PIPE: skipped (ZELLIJ=${ZELLIJ:-<not set>})" >> "$LOG_FILE" 2>/dev/null || true
fi

mkdir -p "${STATUS_DIR}" 2>/dev/null || true
echo "$STATUS" > "${STATUS_DIR}/${AGENT_ID}.state" 2>/dev/null || true
echo "  FILE: written to ${STATUS_DIR}/${AGENT_ID}.state" >> "$LOG_FILE" 2>/dev/null || true

exit 0
