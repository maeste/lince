#!/usr/bin/env bash
#
# 02-broker.sh — sub-issue #253 oracle (blueprint §11).
#
# Broker (Lima wrapper + policy) over a real LimaBackend. Asserts the broker's
# status/exec/snapshot verbs drive a live VM, and that the policy gate refuses an
# out-of-namespace VM name (POLICY_DENIED → exit 13) — proving the broker never
# trusts the client and cannot touch a user's pre-existing Lima instances.
# KVM-gated.
#
# Exit 0 only on success → triggers 03-cli.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "02 broker (#253)"

skip_if_no_kvm

VM="lince-lab-ci02-$$"
SOCK="$LINCE_LAB_SOCK"

cleanup() {
    "$LINCE_LAB_BIN" --socket "$SOCK" vm rm "$VM" -f >/dev/null 2>&1 || true
    stop_broker "$SOCK"
}
trap cleanup EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "broker is reachable (ping)"
assert "$LINCE_LAB_BIN" --socket "$SOCK" lab broker status -- "lab broker status -> reachable"

log "broker drives the real VM lifecycle"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm up "$VM" -- "vm.create + vm.start via broker"

log "broker status/exec/snapshot verbs against the live VM"
assert_exit 0 "broker vm.exec 'true' -> 0" -- "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- true
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot create "$VM" b1 -- "broker snap.create"
SNAP="$("$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot list "$VM")"
assert_contains "$SNAP" "b1" "broker snap.list shows b1"

log "policy gate refuses an out-of-namespace VM name (exit 13)"
assert_exit 13 "policy denies a non lince-lab-* name" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" vm status "not-a-lab-vm"

# ── #253: the broker records the effective egress decision to egress.log ─────
# Running a recipe writes <artifacts>/egress.log with the deny/allow decision the
# run enforces (host-side resolved, never a client value). Use the shipped
# deny-posture generic recipe; assert the log is written and records a decision.
log "recipe.run writes the effective egress decision to egress.log (#253)"
RECIPE="${LINCE_LAB_RECIPE:-$LINCE_LAB_SHARE/recipes/generic-npm.toml}"
if [ ! -f "$RECIPE" ]; then
    REPO_RECIPE="$SCRIPT_DIR/../../../lince-lab/recipes/generic-npm.toml"
    [ -f "$REPO_RECIPE" ] && RECIPE="$REPO_RECIPE"
fi
ARTIFACTS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/lince/lince-lab/artifacts"
EGRESS_LOG="$ARTIFACTS_DIR/egress.log"
rm -f "$EGRESS_LOG" 2>/dev/null || true
# The recipe may pass or fail end-to-end; the egress decision is written first,
# so we only require the log to exist and carry a decision after the run.
"$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$RECIPE" >/dev/null 2>&1 || true
assert_file "$EGRESS_LOG" "egress.log was written by recipe.run"
EGRESS_CONTENT="$(cat "$EGRESS_LOG")"
assert_contains "$EGRESS_CONTENT" '"decision"' "egress.log records an egress decision"

ok "02 broker oracle passed"
exit 0
