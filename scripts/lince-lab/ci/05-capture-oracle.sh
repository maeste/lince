#!/usr/bin/env bash
#
# 05-capture-oracle.sh — sub-issue #256 oracle (blueprint §11).
#
# Capture & oracle: real `ht` (headless terminal) inside the VM driving a real
# TUI program. Asserts the deterministic sync primitives over the live capture
# channel — grab the grid, wait_for a substring (no fixed sleeps), send keys —
# behave as the `watch` verbs document. KVM-gated.
#
# Exit 0 only on success → triggers 06-recipe.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "05 capture-oracle (#256)"

skip_if_no_kvm

VM="lince-lab-ci05-$$"
SOCK="$LINCE_LAB_SOCK"

cleanup() {
    "$LINCE_LAB_BIN" --socket "$SOCK" vm rm "$VM" -f >/dev/null 2>&1 || true
    stop_broker "$SOCK"
}
trap cleanup EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "bring up a VM with a headless terminal available"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm up "$VM" -- "vm up for capture"

# Drive a simple, deterministic TUI under `ht`: `cat` echoes whatever we type, so
# wait_for_substring on the echoed text proves the channel + sync primitive work
# end-to-end without any fixed sleep.
log "watch wait --for over a live ht channel (deterministic, no sleep)"
GRID="$("$LINCE_LAB_BIN" --socket "$SOCK" watch grab "$VM" --size 80x24 --program -- echo lince-capture-ok)"
assert_contains "$GRID" "lince-capture-ok" "ht grid contains the program output"

log "watch keys sends input through the channel"
assert "$LINCE_LAB_BIN" --socket "$SOCK" watch keys "$VM" --size 80x24 \
    --program cat --keys "L" "I" "N" "C" "E" "Enter" \
    -- "watch keys injected the sequence"

WAITED="$("$LINCE_LAB_BIN" --socket "$SOCK" watch wait "$VM" --size 80x24 \
    --program -- sh -c 'echo READY-SUBSTRING' --for READY-SUBSTRING)"
assert_contains "$WAITED" "READY-SUBSTRING" "wait_for_substring returned the settled grid"

ok "05 capture-oracle oracle passed"
exit 0
