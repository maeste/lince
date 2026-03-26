#!/usr/bin/env bash
# claude-status-hook.sh — Claude Code hook that reports agent status
# to the lince-dashboard Zellij plugin via pipe (primary) and file (fallback).
#
# Claude Code pipes JSON to stdin with fields:
#   hook_event_name, session_id, transcript_path, cwd, ...
#   For Notification events: notification_type
#   For PreToolUse events: tool_name
#
# Environment:
#   LINCE_AGENT_ID  — set by the dashboard when spawning the agent
#   ZELLIJ          — set by Zellij when running inside a session
#   LINCE_STATUS_DIR — override for status file directory (default: /tmp/lince-dashboard)

set -euo pipefail

AGENT_ID="${LINCE_AGENT_ID:-}"
STATUS_DIR="${LINCE_STATUS_DIR:-/tmp/lince-dashboard}"
LOG_FILE="/tmp/lince-dashboard/hook-debug.log"

# Always log — even if AGENT_ID is empty — so we can see if hooks fire at all
mkdir -p /tmp/lince-dashboard 2>/dev/null || true
{
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    echo "  AGENT_ID=${AGENT_ID:-<empty>}"
    echo "  ZELLIJ=${ZELLIJ:-<not set>}"
    echo "  ZELLIJ_SESSION=${ZELLIJ_SESSION_NAME:-<not set>}"
    echo "  PWD=$PWD"
    echo "  PATH_has_zellij=$(command -v zellij 2>/dev/null || echo 'NO')"
} >> "$LOG_FILE" 2>/dev/null || true

# Exit silently if we don't know which agent this is
if [ -z "$AGENT_ID" ]; then
    echo "  EXIT: no AGENT_ID" >> "$LOG_FILE" 2>/dev/null || true
    exit 0
fi

# Read stdin JSON (Claude Code hook payload)
INPUT=""
if [ ! -t 0 ]; then
    INPUT=$(cat)
fi

# Cache jq availability once (avoid repeated command -v calls)
HAS_JQ=false
command -v jq >/dev/null 2>&1 && HAS_JQ=true

# Extract a field from the JSON input (jq first, bash regex fallback).
extract_json_field() {
    local field="$1"
    if $HAS_JQ && [ -n "$INPUT" ]; then
        local val
        val=$(echo "$INPUT" | jq -r ".$field // empty" 2>/dev/null || true)
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

HOOK_EVENT=$(extract_json_field "hook_event_name")

if [ -z "$HOOK_EVENT" ]; then
    echo "  EXIT: no HOOK_EVENT parsed (input: ${INPUT:0:80})" >> "$LOG_FILE" 2>/dev/null || true
    exit 0
fi
echo "  HOOK_EVENT=$HOOK_EVENT" >> "$LOG_FILE" 2>/dev/null || true

# Map hook events to dashboard status
STATUS=""
TOOL_NAME=""
SUBAGENT_TYPE=""
MODEL=""
case "$HOOK_EVENT" in
    Stop)
        STATUS="idle"
        ;;
    SessionStart)
        STATUS="running"
        MODEL=$(extract_json_field "model")
        ;;
    UserPromptSubmit)
        STATUS="running"
        ;;
    PreToolUse)
        STATUS="running"
        TOOL_NAME=$(extract_json_field "tool_name")
        ;;
    SubagentStart)
        STATUS="subagent_start"
        SUBAGENT_TYPE=$(extract_json_field "agent_type")
        ;;
    SubagentStop)
        STATUS="subagent_stop"
        SUBAGENT_TYPE=$(extract_json_field "agent_type")
        ;;
    Notification)
        NOTIF_TYPE=$(extract_json_field "notification_type")
        case "${NOTIF_TYPE:-}" in
            idle_prompt)       STATUS="idle" ;;
            permission_prompt) STATUS="permission" ;;
            *)                 STATUS="running" ;;
        esac
        ;;
    *)
        STATUS="running"
        ;;
esac

if [ -z "$STATUS" ]; then
    exit 0
fi

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "")

# Build JSON payload safely with jq if available, string concat as fallback
if $HAS_JQ; then
    PAYLOAD=$(jq -nc \
        --arg id "$AGENT_ID" \
        --arg event "$STATUS" \
        --arg ts "$TIMESTAMP" \
        --arg tool "${TOOL_NAME:-}" \
        --arg subtype "${SUBAGENT_TYPE:-}" \
        --arg model "${MODEL:-}" \
        '{agent_id: $id, event: $event, timestamp: $ts} + (if $tool != "" then {tool_name: $tool} else {} end) + (if $subtype != "" then {subagent_type: $subtype} else {} end) + (if $model != "" then {model: $model} else {} end)')
else
    PAYLOAD="{\"agent_id\":\"${AGENT_ID}\",\"event\":\"${STATUS}\",\"timestamp\":\"${TIMESTAMP}\""
    if [ -n "${TOOL_NAME:-}" ]; then
        PAYLOAD="${PAYLOAD},\"tool_name\":\"${TOOL_NAME}\""
    fi
    if [ -n "${SUBAGENT_TYPE:-}" ]; then
        PAYLOAD="${PAYLOAD},\"subagent_type\":\"${SUBAGENT_TYPE}\""
    fi
    if [ -n "${MODEL:-}" ]; then
        PAYLOAD="${PAYLOAD},\"model\":\"${MODEL}\""
    fi
    PAYLOAD="${PAYLOAD}}"
fi

# Merge token data from statusline cache (if available)
TOKEN_FILE="${STATUS_DIR}/tokens-${AGENT_ID}.json"
if [ -f "$TOKEN_FILE" ]; then
    if $HAS_JQ; then
        TOK_IN=$(jq -r '.tokens_in // 0' "$TOKEN_FILE" 2>/dev/null || echo "0")
        TOK_OUT=$(jq -r '.tokens_out // 0' "$TOKEN_FILE" 2>/dev/null || echo "0")
    else
        TOK_CONTENT=$(cat "$TOKEN_FILE" 2>/dev/null || echo "")
        TOK_IN=0; TOK_OUT=0
        [[ "$TOK_CONTENT" =~ \"tokens_in\":([0-9]+) ]] && TOK_IN="${BASH_REMATCH[1]}"
        [[ "$TOK_CONTENT" =~ \"tokens_out\":([0-9]+) ]] && TOK_OUT="${BASH_REMATCH[1]}"
    fi
    if [ "$TOK_IN" -gt 0 ] || [ "$TOK_OUT" -gt 0 ]; then
        if $HAS_JQ; then
            PAYLOAD=$(echo "$PAYLOAD" | jq -c --argjson ti "$TOK_IN" --argjson to "$TOK_OUT" '. + {tokens_in: $ti, tokens_out: $to}')
        else
            PAYLOAD="${PAYLOAD%\}},\"tokens_in\":${TOK_IN},\"tokens_out\":${TOK_OUT}}"
        fi
    fi
fi

echo "  STATUS=$STATUS  PAYLOAD=$PAYLOAD" >> "$LOG_FILE" 2>/dev/null || true

# Primary: send via zellij pipe (if inside a Zellij session)
if [ -n "${ZELLIJ:-}" ] && command -v zellij >/dev/null 2>&1; then
    PIPE_OUT=$(echo "$PAYLOAD" | timeout 2 zellij pipe --name "claude-status" 2>&1) && \
        echo "  PIPE: ok" >> "$LOG_FILE" || \
        echo "  PIPE: failed ($PIPE_OUT)" >> "$LOG_FILE" 2>/dev/null || true
else
    echo "  PIPE: skipped (ZELLIJ=${ZELLIJ:-<not set>})" >> "$LOG_FILE" 2>/dev/null || true
fi

# Fallback: write status to file (always, as backup)
mkdir -p "${STATUS_DIR}" 2>/dev/null || true
echo "$STATUS" > "${STATUS_DIR}/claude-${AGENT_ID}.state" 2>/dev/null || true
echo "  FILE: written to ${STATUS_DIR}/claude-${AGENT_ID}.state" >> "$LOG_FILE" 2>/dev/null || true

exit 0
