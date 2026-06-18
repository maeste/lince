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

SOCK="$LINCE_LAB_SOCK"
RECIPE="${LINCE_LAB_RECIPE:-$LINCE_LAB_SHARE/recipes/generic-npm.toml}"
if [ ! -f "$RECIPE" ]; then
    REPO_RECIPE="$SCRIPT_DIR/../../../lince-lab/recipes/generic-npm.toml"
    [ -f "$REPO_RECIPE" ] && RECIPE="$REPO_RECIPE"
fi

# ── Part 1: SUBSTRATE-FREE checks (run even without KVM, like oracle 06) ─────
# The "this is a GENERAL oracle, not Lince-specific" proof must run on a no-KVM
# host too, so the recipe-validate + the no-Lince-paths grep happen BEFORE the
# skip_if_no_kvm gate. Use a FakeBackend-backed broker for the validate.
cleanup_fake() { stop_broker "$SOCK"; }
trap cleanup_fake EXIT

assert_file "$RECIPE" "generic-npm recipe present"

log "substrate-free: the generic recipe validates (non-Lince, allowlisted fetch)"
LINCE_LAB_FAKE=1 start_broker "$SOCK"
assert_exit 0 "run validate generic-npm -> 0" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run validate "$RECIPE"

# The recipe must be GENERIC: it may not bake in any Lince-specific path. If it
# referenced e.g. lince-config / agent-sandbox / ~/.config/lince it would not be
# the "general disposable-VM oracle" #261 requires — fail if any such path leaks.
log "the generic recipe contains no Lince-specific paths (#261)"
if grep -Eiq 'lince-config|agent-sandbox|lince-dashboard|\.config/lince|lince\.toml|enabled_agents' "$RECIPE"; then
    bad "generic recipe references a Lince-specific path (not a general oracle)"
    grep -Ein 'lince-config|agent-sandbox|lince-dashboard|\.config/lince|lince\.toml|enabled_agents' "$RECIPE" >&2
    exit 1
fi
ok "generic recipe contains no Lince-specific paths"

# Tear down the fake broker before the KVM part (which uses the real backend).
stop_broker "$SOCK"
trap - EXIT

# ── Part 2: real recipe.run in a VM (KVM-gated) ─────────────────────────────
skip_if_no_kvm

cleanup_real() { stop_broker "$SOCK"; }
trap cleanup_real EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "run the generic-npm recipe end-to-end under the networked preset"
assert_exit 0 "run recipe generic-npm -> 0 in a real VM" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$RECIPE"

ok "10 generic oracle passed"
exit 0
