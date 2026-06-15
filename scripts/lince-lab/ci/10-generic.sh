#!/usr/bin/env bash
#
# 10-generic.sh — sub-issue #261 oracle (blueprint §11).
#
# Generalization: a non-Lince recipe. Runs the shipped `generic-npm` recipe in a
# real VM under the `networked` preset — installing + testing an npm package via
# an allowlisted fetch — proving lince-lab is a general disposable-VM oracle, not
# Lince-specific, while the deny-by-default network posture still holds (only the
# recipe's explicit allow_hosts/allow_ports are reachable, no host credentials).
# KVM-gated. This is the terminal link of the oracle chain.
#
# Exit 0 only on success.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "10 generic (#261)"

skip_if_no_kvm

SOCK="$LINCE_LAB_SOCK"
RECIPE="${LINCE_LAB_RECIPE:-$LINCE_LAB_SHARE/recipes/generic-npm.toml}"
if [ ! -f "$RECIPE" ]; then
    REPO_RECIPE="$SCRIPT_DIR/../../../lince-lab/recipes/generic-npm.toml"
    [ -f "$REPO_RECIPE" ] && RECIPE="$REPO_RECIPE"
fi

cleanup() { stop_broker "$SOCK"; }
trap cleanup EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "the generic recipe validates (non-Lince, allowlisted fetch)"
assert_file "$RECIPE" "generic-npm recipe present"
assert_exit 0 "run validate generic-npm -> 0" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run validate "$RECIPE"

log "run the generic-npm recipe end-to-end under the networked preset"
assert_exit 0 "run recipe generic-npm -> 0 in a real VM" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$RECIPE"

ok "10 generic oracle passed"
exit 0
