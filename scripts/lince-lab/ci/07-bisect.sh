#!/usr/bin/env bash
#
# 07-bisect.sh — sub-issue #258 oracle (blueprint §11).
#
# Bisect loop. Seeds a small git repo with a known regression commit, then runs
# `lince-lab find bisect` using a recipe as the verdict oracle and asserts the
# loop converges on the correct first-bad commit, writing a well-formed
# bisect.json. The substrate is reset between candidates via the base snapshot.
# KVM-gated.
#
# Exit 0 only on success → triggers 08-lince-fixtures.sh.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-lib.sh
source "$SCRIPT_DIR/00-lib.sh"

oracle_header "07 bisect (#258)"

skip_if_no_kvm

SOCK="$LINCE_LAB_SOCK"
RECIPE="${LINCE_LAB_RECIPE:-$LINCE_LAB_SHARE/recipes/generic-npm.toml}"
if [ ! -f "$RECIPE" ]; then
    REPO_RECIPE="$SCRIPT_DIR/../../../lince-lab/recipes/generic-npm.toml"
    [ -f "$REPO_RECIPE" ] && RECIPE="$REPO_RECIPE"
fi

WORK="$(mktemp -d)"
REPO="$WORK/seeded-repo"
OUT="$WORK/bisect.json"

cleanup() {
    stop_broker "$SOCK"
    rm -rf "$WORK"
}
trap cleanup EXIT

log "seed a linear repo with a known regression"
git init -q "$REPO"
git -C "$REPO" config user.email ci@lince.local
git -C "$REPO" config user.name "lince ci"
echo "ok" >"$REPO/marker"
git -C "$REPO" add marker && git -C "$REPO" commit -qm c1
GOOD="$(git -C "$REPO" rev-parse HEAD)"
echo "ok" >"$REPO/marker" && git -C "$REPO" commit -qam c2 --allow-empty
echo "ok" >"$REPO/marker" && git -C "$REPO" commit -qam c3 --allow-empty
# The regression: marker flips to a failing value here (first-bad).
echo "regression" >"$REPO/marker"
git -C "$REPO" commit -qam c4-regression
FIRST_BAD="$(git -C "$REPO" rev-parse HEAD)"
git -C "$REPO" commit -qam c5 --allow-empty
BAD="$(git -C "$REPO" rev-parse HEAD)"

log "run find bisect over the live broker"
LINCE_LAB_FAKE="" start_broker "$SOCK"
"$LINCE_LAB_BIN" --socket "$SOCK" find bisect "$RECIPE" \
    --good "$GOOD" --bad "$BAD" --repo-dir "$REPO" --out "$OUT"

log "bisect.json is well-formed and converged on the seeded first-bad commit"
assert_file "$OUT" "bisect.json written"
REPORTED="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("first_bad",""))' "$OUT")"
STATUS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status",""))' "$OUT")"
assert_eq "$STATUS" "converged" "bisect status converged"
assert_eq "$REPORTED" "$FIRST_BAD" "first_bad matches the seeded regression"

ok "07 bisect oracle passed"
exit 0
