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
# The capture program must satisfy two constraints:
#   1) LONG-LIVED so ht keeps its grid up for the snapshot (a print-then-exit
#      program races ht's teardown — the old "timed out waiting for terminal
#      snapshot" flake).
#   2) SIMPLE argv — no space-containing element, no shell metacharacters —
#      because `limactl shell` word-splits a multi-word arg in transit (a
#      `sh -c '...; ...'` script gets mangled in the guest). `yes <marker>` meets
#      both: it floods the marker forever (long-lived) with single-word argv that
#      survives the transport, and exits cleanly when the channel closes.
GRID="$("$LINCE_LAB_BIN" --socket "$SOCK" watch wait "$VM" --size 80x24 --cmd-timeout 30 --for lince-capture-ok --program yes lince-capture-ok)"
assert_contains "$GRID" "lince-capture-ok" "ht grid contains the program output"

log "watch keys sends input through the channel"
# --program uses argparse.REMAINDER, so it must be LAST (it swallows everything
# after it); other flags (--keys/--for/--size/--png) come before it, no `--`.
assert "$LINCE_LAB_BIN" --socket "$SOCK" watch keys "$VM" --size 80x24 \
    --keys "L" "I" "N" "C" "E" "Enter" --program cat \
    -- "watch keys injected the sequence"

WAITED="$("$LINCE_LAB_BIN" --socket "$SOCK" watch wait "$VM" --size 80x24 \
    --cmd-timeout 30 --for READY-SUBSTRING --program yes READY-SUBSTRING)"
assert_contains "$WAITED" "READY-SUBSTRING" "wait_for_substring returned the settled grid"

# ── #256: pixel-PNG capture artifact (optional Pillow layer over the grid) ───
# `watch grab --png NAME` renders the captured grid to <artifacts>/NAME.png when
# Pillow is installed, else writes <artifacts>/NAME.txt (no fake PNG). This checks
# the RENDER/ARTIFACT layer (a valid PNG, or an honest .txt fallback). Content
# capture itself is proven deterministically by the `watch wait --for` checks
# above — `grab` is an instant snapshot, so it cannot deterministically assert a
# specific grid string. The program is long-lived (`cat`) so ht stays alive for
# the snapshot rather than racing a program that prints-then-exits.
log "watch grab --png writes a capture artifact under the artifacts root (#256)"
ARTIFACTS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lince/lince-lab/artifacts"
CAP_NAME="ci05-capture-$$"
rm -f "$ARTIFACTS_DIR/$CAP_NAME.png" "$ARTIFACTS_DIR/$CAP_NAME.txt" 2>/dev/null || true
"$LINCE_LAB_BIN" --socket "$SOCK" watch grab "$VM" --size 80x24 \
    --cmd-timeout 30 --png "$CAP_NAME" --program yes lince-png-ok >/dev/null
if python3 -c 'import PIL' >/dev/null 2>&1; then
    PNG="$ARTIFACTS_DIR/$CAP_NAME.png"
    assert_file "$PNG" "PNG capture artifact written (Pillow present)"
    # PNG validity: the 8-byte signature must be \x89PNG\r\n\x1a\n.
    SIG="$(head -c 8 "$PNG" | od -An -tx1 | tr -d ' \n')"
    assert_eq "$SIG" "89504e470d0a1a0a" "capture artifact is a valid PNG (magic bytes)"
    rm -f "$PNG"
else
    TXT="$ARTIFACTS_DIR/$CAP_NAME.txt"
    assert_file "$TXT" "text capture artifact written (Pillow absent — honest fallback)"
    rm -f "$TXT"
fi

ok "05 capture-oracle oracle passed"
exit 0
