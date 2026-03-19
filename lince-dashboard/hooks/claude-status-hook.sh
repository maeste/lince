#!/usr/bin/env bash
# claude-status-hook.sh — Claude Code hook that reports agent status
# to the lince-dashboard Zellij plugin via pipe (primary) and file (fallback).
#
# Claude Code pipes JSON to stdin with fields:
#   hook_event_name, session_id, transcript_path, cwd, ...
#   For Notification events: notification_type
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

# Parse hook event name — try jq first, fall back to grep
HOOK_EVENT=""
if command -v jq >/dev/null 2>&1 && [ -n "$INPUT" ]; then
    HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null || true)
fi

# Fallback: extract with bash pattern matching
if [ -z "$HOOK_EVENT" ] && [ -n "$INPUT" ]; then
    # Match "hook_event_name":"VALUE"
    if [[ "$INPUT" =~ \"hook_event_name\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
        HOOK_EVENT="${BASH_REMATCH[1]}"
    fi
fi

if [ -z "$HOOK_EVENT" ]; then
    echo "  EXIT: no HOOK_EVENT parsed (input: ${INPUT:0:80})" >> "$LOG_FILE" 2>/dev/null || true
    exit 0
fi
echo "  HOOK_EVENT=$HOOK_EVENT" >> "$LOG_FILE" 2>/dev/null || true

# Map hook events to dashboard status
STATUS=""
case "$HOOK_EVENT" in
    Stop)
        # Claude finished its turn and is waiting for user input
        STATUS="idle"
        ;;
    UserPromptSubmit | PreToolUse)
        STATUS="running"
        ;;
    Notification)
        # Extract notification_type
        NOTIF_TYPE=""
        if command -v jq >/dev/null 2>&1 && [ -n "$INPUT" ]; then
            NOTIF_TYPE=$(echo "$INPUT" | jq -r '.notification_type // empty' 2>/dev/null || true)
        fi
        if [ -z "$NOTIF_TYPE" ] && [ -n "$INPUT" ]; then
            if [[ "$INPUT" =~ \"notification_type\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
                NOTIF_TYPE="${BASH_REMATCH[1]}"
            fi
        fi
        case "$NOTIF_TYPE" in
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
PAYLOAD="{\"agent_id\":\"${AGENT_ID}\",\"event\":\"${STATUS}\",\"timestamp\":\"${TIMESTAMP}\"}"

echo "  STATUS=$STATUS  PAYLOAD=$PAYLOAD" >> "$LOG_FILE" 2>/dev/null || true

# Primary: send via zellij pipe (if inside a Zellij session)
if [ -n "${ZELLIJ:-}" ] && command -v zellij >/dev/null 2>&1; then
    # Timeout after 2s to avoid blocking Claude Code if socket is unreachable
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
