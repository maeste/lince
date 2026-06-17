#!/usr/bin/env bash
#
# probe-ht-stream.sh — diagnostic for the shipped `ht` binary's stdio event
# behavior over a PIPE (exactly how LimaCaptureChannel drives it). No VM needed.
#
# Two tests, each time-stamped ([+Xs] = seconds since that test launched):
#
#   TEST A — passive subscribe: subscribe to init/output/snapshot, send NO
#            commands, child prints a marker then sleeps. Tells us whether ht
#            emits init/output PROACTIVELY over a pipe.
#
#   TEST B — active snapshot (mirrors `watch grab` and our wait_for_substring):
#            subscribe, then send {"type":"takeSnapshot"} on stdin while the child
#            is still ALIVE, and read the reply. Tells us whether ht answers
#            takeSnapshot over a pipe with a grid containing the marker — this is
#            the path the real oracle uses, so TEST B passing ⇒ oracle 05 should
#            pass with the read_line deadline fix.
#
# Usage: bash scripts/lince-lab/ci/probe-ht-stream.sh

set -u

# ── resolve the ht binary (env override → XDG → default), like the broker ─────
if [ -n "${LINCE_LAB_HT:-}" ]; then
    HT="$LINCE_LAB_HT"
else
    SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/lince/lince-lab"
    HT="$SHARE/bin/ht"
fi

echo "=== ht stdio probe ==="
echo "ht binary: $HT"
if [ ! -x "$HT" ]; then
    echo "ERROR: ht not found / not executable at: $HT" >&2
    exit 1
fi
echo -n "ht version: "; "$HT" --version 2>&1 || echo "(no --version)"

# stamp: read lines on stdin, print each with elapsed seconds since START.
stamp() {
    local start="$1" now elapsed
    while IFS= read -r line; do
        now="$(date +%s.%N)"
        elapsed="$(awk -v s="$start" -v n="$now" 'BEGIN { printf "%5.2f", n - s }')"
        printf '   [+%ss] %s\n' "$elapsed" "$(printf '%s' "$line" | cut -c1-110)"
    done
}

echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo "TEST A — passive subscribe (no commands); child: echo MARKER; sleep 5"
echo "  expect (if ht streams proactively): an init line + an output line near +0s"
echo "──────────────────────────────────────────────────────────────────────"
A_START="$(date +%s.%N)"
timeout 7 "$HT" --size 80x24 --subscribe init,output,snapshot \
    -- sh -c 'echo PROBE-MARKER-A; sleep 5' 2>&1 | stamp "$A_START"
echo "   (TEST A done)"

echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo "TEST B — active takeSnapshot while child ALIVE; child: echo MARKER; sleep 6"
echo "  we send {\"type\":\"takeSnapshot\"} on stdin at ~+1.5s and read the reply"
echo "  expect: a snapshot line containing PROBE-MARKER-B  (this is the real path)"
echo "──────────────────────────────────────────────────────────────────────"
B_START="$(date +%s.%N)"
# Feed stdin: wait, send takeSnapshot, keep stdin open a bit so ht stays put.
{ sleep 1.5; printf '%s\n' '{"type":"takeSnapshot"}'; sleep 4; } \
  | timeout 8 "$HT" --size 80x24 --subscribe init,output,snapshot \
        -- sh -c 'echo PROBE-MARKER-B; sleep 6' 2>&1 | stamp "$B_START"
echo "   (TEST B done)"

echo ""
echo "=== verdict guide ==="
echo "• TEST B shows a snapshot line with PROBE-MARKER-B  → ht answers takeSnapshot"
echo "  over a pipe; the oracle-05 hang was only our read_line bug (now fixed) —"
echo "  just re-run oracle 05."
echo "• TEST B shows NOTHING (no snapshot reply at all)   → ht is not emitting over"
echo "  the pipe in this mode; paste the full output and I'll add a PTY-based fix."
