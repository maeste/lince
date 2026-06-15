#!/usr/bin/env bash
#
# 03-cli.sh — sub-issue #254 oracle (blueprint §11).
#
# CLI end-to-end against a broker bound to a live VM. Exercises the full
# CLI → socket → broker → LimaBackend path for the everyday verbs and asserts the
# exit-code propagation contract that the whole oracle chain and the bisect loop
# depend on (a failing guest command surfaces verbatim as the CLI exit code).
# KVM-gated.
#
# Exit 0 only on success → triggers 04-sandbox-socket.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "03 cli (#254)"

skip_if_no_kvm

VM="lince-lab-ci03-$$"
SOCK="$LINCE_LAB_SOCK"

cleanup() {
    "$LINCE_LAB_BIN" --socket "$SOCK" vm rm "$VM" -f >/dev/null 2>&1 || true
    stop_broker "$SOCK"
}
trap cleanup EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "CLI: vm up / status / list against the live broker"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm up "$VM" -- "cli vm up"
LIST="$("$LINCE_LAB_BIN" --socket "$SOCK" vm list)"
assert_contains "$LIST" "$VM" "cli vm list shows $VM"

log "CLI: exit-code propagation (guest code is the CLI code)"
assert_exit 0 "vm exec 'true' -> 0" -- "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- true
assert_exit 1 "vm exec 'false' -> 1" -- "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- false
assert_exit 42 "vm exec 'exit 42' -> 42" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- sh -c 'exit 42'

log "CLI: stdout from the guest reaches the terminal"
OUT="$("$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- sh -c 'echo hello-from-guest')"
assert_contains "$OUT" "hello-from-guest" "guest stdout reaches the CLI"

log "CLI: broker-unreachable maps to exit 69"
assert_exit 69 "unreachable socket -> 69" -- \
    "$LINCE_LAB_BIN" --socket "/nonexistent/lince-lab.sock" vm list

ok "03 cli oracle passed"
exit 0
