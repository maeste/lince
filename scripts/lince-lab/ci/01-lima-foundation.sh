#!/usr/bin/env bash
#
# 01-lima-foundation.sh — sub-issue #252 oracle (blueprint §11).
#
# Lima foundation + ci convention. Asserts the real LimaBackend glue against a
# live QEMU VM: limactl is present, a VM can be created + started, a guest
# command's exit code propagates (the bisect signal), and snapshot
# create/apply/list round-trips. KVM-gated.
#
# Exit 0 only on success → triggers 02-broker.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "01 lima-foundation (#252)"

# VM-dependent: skip cleanly off a KVM host so the chain stays green.
skip_if_no_kvm

VM="lince-lab-ci01-$$"
SOCK="$LINCE_LAB_SOCK"

cleanup() {
    "$LINCE_LAB_BIN" --socket "$SOCK" vm rm "$VM" -f >/dev/null 2>&1 || true
    stop_broker "$SOCK"
}
trap cleanup EXIT

# A live broker over the real LimaBackend is the seam the CLI drives.
LINCE_LAB_FAKE="" start_broker "$SOCK"

log "create + start a disposable VM"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm up "$VM" -- "vm up created and started $VM"

log "VM reports running"
STATUS_JSON="$("$LINCE_LAB_BIN" --socket "$SOCK" --json vm status "$VM")"
assert_contains "$STATUS_JSON" '"running"' "vm status reports running"

log "guest exit code propagates (the bisect signal)"
assert_exit 0 "exec 'true' -> 0" -- "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- true
assert_exit 7 "exec 'exit 7' -> 7" -- "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- sh -c 'exit 7'

log "snapshot create / list / apply round-trip"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot create "$VM" base -- "snapshot create base"
SNAP_LIST="$("$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot list "$VM")"
assert_contains "$SNAP_LIST" "base" "snapshot list shows base"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot apply "$VM" base -- "snapshot apply base (reset)"

ok "01 lima-foundation oracle passed"
exit 0
