#!/usr/bin/env bash
#
# 08-lince-fixtures.sh — sub-issue #259 oracle (blueprint §11).
#
# Lince fixtures. Drives the two real Lince fixture recipes in a VM:
#   • lince-wizard.toml  — drive `lince-config quickstart` to completion via ht
#                          and assert the config file is written.
#   • lince-installer.toml — run install.sh twice and assert the second run is a
#                          clean idempotent no-op (exit 0 unchanged).
# Both recipes are the everyday entry point exercised against a real substrate.
# KVM-gated.
#
# Exit 0 only on success → triggers 09-packaging.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "08 lince-fixtures (#259)"

skip_if_no_kvm

SOCK="$LINCE_LAB_SOCK"

# Resolve the two shipped fixture recipes (installed share, else in-repo tree).
resolve_recipe() {
    local name="$1"
    local installed="$LINCE_LAB_SHARE/recipes/$name"
    local in_repo="$SCRIPT_DIR/../../../lince-lab/recipes/$name"
    if [ -f "$installed" ]; then
        echo "$installed"
    else
        echo "$in_repo"
    fi
}
WIZARD_RECIPE="$(resolve_recipe lince-wizard.toml)"
INSTALLER_RECIPE="$(resolve_recipe lince-installer.toml)"

cleanup() { stop_broker "$SOCK"; }
trap cleanup EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "drive the lince quickstart wizard to completion (#259 wizard fixture)"
assert_file "$WIZARD_RECIPE" "lince-wizard recipe present"
assert_exit 0 "run recipe lince-wizard -> 0" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$WIZARD_RECIPE"

log "install.sh run-twice idempotency (#259 installer fixture)"
assert_file "$INSTALLER_RECIPE" "lince-installer recipe present"
assert_exit 0 "run recipe lince-installer -> 0 (idempotent)" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$INSTALLER_RECIPE"

ok "08 lince-fixtures oracle passed"
exit 0
