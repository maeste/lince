#!/usr/bin/env bash
#
# 04-sandbox-socket.sh — sub-issue #255 oracle (blueprint §11).
#
# Sandbox socket integration: an agent running INSIDE the bwrap sandbox reaches
# the broker socket and drives a real VM. Proves the §2c-style --bind of the
# broker socket into the sandbox (and the paranoid socat bridge) lets the
# sandboxed agent command the host-side broker — and nothing else. KVM-gated
# (and additionally requires bwrap; missing bwrap is a SKIP, not a failure).
#
# Exit 0 only on success → triggers 05-capture-oracle.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "04 sandbox-socket (#255)"

skip_if_no_kvm

# bwrap is the sandbox engine; without it the integration cannot run — skip.
if ! command -v bwrap >/dev/null 2>&1; then
    echo -e "${YELLOW}SKIP:${NC} bwrap not installed (sandbox engine unavailable)"
    exit 0
fi

VM="lince-lab-ci04-$$"
SOCK="$LINCE_LAB_SOCK"

cleanup() {
    "$LINCE_LAB_BIN" --socket "$SOCK" vm rm "$VM" -f >/dev/null 2>&1 || true
    stop_broker "$SOCK"
}
trap cleanup EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "host-side: bring up the VM the sandboxed agent will drive"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm up "$VM" -- "host vm up"

# Run the CLI inside a minimal bwrap that mirrors the sandbox's broker-socket
# --bind idiom (§2c): the whole FS read-only, a fresh /tmp, the broker socket
# bind-mounted RW at the same path host+sandbox. The sandboxed CLI must reach the
# broker and propagate the guest exit code out through the sandbox boundary.
run_in_bwrap() {
    bwrap \
        --ro-bind / / \
        --tmpfs /tmp \
        --bind "$(dirname "$SOCK")" "$(dirname "$SOCK")" \
        --dev /dev \
        --proc /proc \
        -- "$@"
}

log "sandboxed agent reaches the broker over the bound socket"
assert run_in_bwrap "$LINCE_LAB_BIN" --socket "$SOCK" lab broker status \
    -- "broker reachable from inside bwrap"

log "sandboxed agent drives the VM (exit code crosses the sandbox boundary)"
assert_exit 0 "in-sandbox vm exec 'true' -> 0" -- \
    run_in_bwrap "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- true
assert_exit 5 "in-sandbox vm exec 'exit 5' -> 5" -- \
    run_in_bwrap "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- sh -c 'exit 5'

ok "04 sandbox-socket oracle passed"
exit 0
