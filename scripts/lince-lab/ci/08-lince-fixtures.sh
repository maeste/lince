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
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Both fixture recipes install lince-config + stage the agent registry FROM the
# staged workspace (/work). The committed fixtures/lince-clone is a placeholder
# (it only carries verify-agents.py + lince-toml-seed.toml so host_dir resolves
# and the substrate-free test works). For a real run we overlay the actual
# lince-config/ sources + registry.d/ into a throwaway copy of the recipe dir and
# point the recipes at THAT — never mutating the committed/installed fixture.
STAGE="$(mktemp -d)"
FIX="$STAGE/fixtures/lince-clone"
mkdir -p "$FIX"
cp "$WIZARD_RECIPE" "$STAGE/lince-wizard.toml"
cp "$INSTALLER_RECIPE" "$STAGE/lince-installer.toml"
SRC_FIX="$(dirname "$WIZARD_RECIPE")/fixtures/lince-clone"
cp "$SRC_FIX/verify-agents.py" "$FIX/"
cp "$SRC_FIX/lince-toml-seed.toml" "$FIX/"
cp -r "$REPO_ROOT/lince-config" "$FIX/lince-config"
cp -r "$REPO_ROOT/registry.d" "$FIX/registry.d"
# Drop bytecode caches the copy may have carried over.
find "$FIX/lince-config" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
STAGED_WIZARD="$STAGE/lince-wizard.toml"
STAGED_INSTALLER="$STAGE/lince-installer.toml"

cleanup() { stop_broker "$SOCK"; rm -rf "$STAGE"; }
trap cleanup EXIT

LINCE_LAB_FAKE="" start_broker "$SOCK"

log "verify the resolved New-Agent list == enabled_agents, each once (#202 wizard fixture)"
assert_file "$WIZARD_RECIPE" "lince-wizard recipe present"
assert_file "$FIX/lince-config/install.sh" "real lince-config sources staged into the workspace"
assert_exit 0 "run recipe lince-wizard -> 0" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$STAGED_WIZARD"

log "install.sh run-twice idempotency (#259 installer fixture)"
assert_file "$INSTALLER_RECIPE" "lince-installer recipe present"
assert_exit 0 "run recipe lince-installer -> 0 (idempotent)" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" run recipe "$STAGED_INSTALLER"

ok "08 lince-fixtures oracle passed"
exit 0
