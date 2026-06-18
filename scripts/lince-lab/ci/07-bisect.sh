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

# The verdict recipe must test the STAGED REPO (the bisect copies each candidate's
# checkout into the workspace), not install an unrelated package. Generate a
# marker recipe whose single step passes iff the repo's marker reads 'ok' — so
# good commits verdict good and the regression (marker='regression') verdicts bad.
# (The shipped generic-npm recipe ignores the repo, so every candidate would look
# good — that is NOT a valid bisect oracle.) A deny network posture: the check is
# purely local, no egress needed.
log "write the bisect verdict recipe (verdict = staged repo's marker reads 'ok')"
RECIPE_DIR="$WORK/recipe"
mkdir -p "$RECIPE_DIR/ws"
: >"$RECIPE_DIR/ws/.keep"
RECIPE="${LINCE_LAB_RECIPE:-$RECIPE_DIR/bisect-marker.toml}"
if [ ! -f "$RECIPE" ]; then
    cat >"$RECIPE_DIR/bisect-marker.toml" <<'TOML'
[recipe]
name = "bisect-marker"
description = "Bisect verdict oracle: the staged repo's marker file must read 'ok' (the seeded regression flips it to 'regression')."
version = "1"

[vm]
image = "fedora"

[network]
mode = "deny"

[workspace]
host_dir = "./ws"
guest_dir = "/work"

[[step]]
name = "check-marker"
# Bisect stages the checked-out repo into /work. Pass iff the marker reads 'ok';
# robust to whether the copy lands the repo's contents directly at /work or under
# a subdirectory.
run = ["sh", "-c", "grep -hqx ok /work/marker /work/*/marker 2>/dev/null"]

[assert]
exit_code = 0
TOML
    RECIPE="$RECIPE_DIR/bisect-marker.toml"
fi

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
