#!/usr/bin/env bash
#
# 06-recipe.sh — sub-issue #257 oracle (blueprint §11).
#
# Recipe contract. Two parts:
#   1. SUBSTRATE-FREE (runs even without KVM, NOT gated by skip_if_no_kvm):
#      `lince-lab run validate <recipe>` over a FakeBackend-backed broker. Proves
#      the recipe schema validates (exit 0) and a malformed recipe is rejected
#      with the documented data-error code (exit 65). This part needs no VM.
#   2. KVM-gated: `lince-lab run recipe <recipe>` end-to-end in a real VM.
#
# Exit 0 only on success → triggers 07-bisect.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "06 recipe (#257)"

SOCK="$LINCE_LAB_SOCK"
# A shipped recipe to validate. Resolve from the installed share dir, falling
# back to the in-repo module tree so the oracle works both installed and in CI.
RECIPE="${LINCE_LAB_RECIPE:-$LINCE_LAB_SHARE/recipes/generic-npm.toml}"
if [ ! -f "$RECIPE" ]; then
    REPO_RECIPE="$SCRIPT_DIR/../../../lince-lab/recipes/generic-npm.toml"
    [ -f "$REPO_RECIPE" ] && RECIPE="$REPO_RECIPE"
fi

# ── Part 1: substrate-free validation (FakeBackend broker, no KVM) ──────────
cleanup_fake() { stop_broker "$SOCK"; }
trap cleanup_fake EXIT

log "substrate-free: start a FakeBackend broker for validation"
LINCE_LAB_FAKE=1 start_broker "$SOCK"

log "run validate accepts a well-formed shipped recipe (exit 0)"
assert_file "$RECIPE" "shipped recipe is present"
assert_exit 0 "run validate <recipe> -> 0" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run validate "$RECIPE"

log "run validate rejects a malformed recipe (exit 65)"
BADDIR="$(mktemp -d)"
BAD_RECIPE="$BADDIR/bad.toml"
# Missing the mandatory [assert] table → DataError → exit 65.
cat >"$BAD_RECIPE" <<'EOF'
[recipe]
name = "bad"
[vm]
image = "fedora"
[workspace]
host_dir = "."
guest_dir = "/work"
EOF
assert_exit 65 "run validate <malformed> -> 65" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run validate "$BAD_RECIPE"
rm -rf "$BADDIR"

# Tear down the fake broker before the KVM part (which uses the real backend).
stop_broker "$SOCK"
trap - EXIT

# ── Part 2: real recipe.run in a VM (KVM-gated) ─────────────────────────────
skip_if_no_kvm

cleanup_real() { stop_broker "$SOCK"; }
trap cleanup_real EXIT

log "KVM: start a real LimaBackend broker and run the recipe end-to-end"
LINCE_LAB_FAKE="" start_broker "$SOCK"
assert_exit 0 "run recipe <recipe> -> 0 in a real VM" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$RECIPE"

ok "06 recipe oracle passed"
exit 0
