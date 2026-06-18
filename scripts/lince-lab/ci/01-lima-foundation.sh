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

# ── --assert-no-host-mounts canary (the L1/L7 isolation invariant) ───────────
# The policy-forced template sets mounts:[] so NO host filesystem is exposed.
# Prove it: a host-only file must NOT be readable from inside the guest. We
# create the file in a host-only temp so it cannot legitimately appear in the
# guest; `cat`-ing it MUST fail. The optional --assert-no-host-mounts flag is
# accepted as a no-op label (the canary is a core invariant and always runs).
case "${1:-}" in --assert-no-host-mounts) shift ;; esac
log "canary: no host mount is visible inside the guest (cat host file -> must fail)"
HOST_CANARY="$(mktemp)"
echo "host-only-secret-$$" >"$HOST_CANARY"
# The guest has no mount of the host fs, so cat-ing this absolute host path from
# inside the VM must fail — a nonzero exit is the required (passing) outcome.
assert_exit 1 "guest cannot cat a host-only file (no host mount)" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- cat "$HOST_CANARY"
rm -f "$HOST_CANARY"

# ── base userspace smoke ─────────────────────────────────────────────────────
# A bare `vm up` boots the minimal cloud image WITH the deny-by-default egress
# cut, so it carries only the base userspace — NOT a dev toolchain. Heavy
# toolchains (rust + wasm32, node/npm, …) are provisioned PER-RECIPE: a recipe
# declares its own [[provision]] and, when it must fetch packages, runs under the
# `networked` posture. Baking them into every lab VM would be slow and is
# impossible here anyway (egress is denied). So the foundation oracle asserts the
# real invariant: exec reaches a working Linux userspace with a usable
# interpreter (python3 ships with the Fedora Cloud image via cloud-init).
log "base userspace smoke (Linux guest + sh + python3)"
UNAME_OUT="$("$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- uname -s)"
assert_contains "$UNAME_OUT" "Linux" "guest is a Linux userspace"
assert_exit 0 "sh present"      -- "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- sh -c 'command -v sh'
assert_exit 0 "python3 present" -- "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- sh -c 'command -v python3'

# ── network-off probe (default-deny egress, L4) ──────────────────────────────
# This VM was created with the deny-by-default boot script (no allowlist), so any
# outbound fetch must fail fast. A successful curl here would mean egress leaked.
log "network-off probe (curl --max-time 5 must FAIL under default-deny)"
NET_CODE=0
"$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- \
    sh -c 'curl --max-time 5 -sS https://example.com >/dev/null' || NET_CODE=$?
if [ "$NET_CODE" -ne 0 ]; then
    ok "egress is denied (curl exited $NET_CODE, as required)"
else
    bad "egress leaked: curl succeeded under default-deny network"
    exit 1
fi

# ── snapshot: create / list / mutate-then-assert-the-mutation-is-gone ────────
# A snapshot must be a true reset: take a base snapshot, mutate the guest fs,
# confirm the mutation is present, restore, then PROVE the mutation is gone.
log "snapshot create / list / apply round-trip with mutate-then-assert-gone"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot create "$VM" base -- "snapshot create base"
SNAP_LIST="$("$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot list "$VM")"
assert_contains "$SNAP_LIST" "base" "snapshot list shows base"

# Lima logs in as a regular (non-root) user with passwordless sudo, so /root is
# not writable — use /tmp (always writable; the running-VM snapshot captures it).
MUTATION="/tmp/.lince-lab-mutation-$$"
log "mutate the guest after the snapshot, then restore and assert it is gone"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- sh -c "touch $MUTATION" \
    -- "mutate guest (create $MUTATION)"
assert_exit 0 "mutation is present before restore" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- test -e "$MUTATION"
assert "$LINCE_LAB_BIN" --socket "$SOCK" vm snapshot apply "$VM" base -- "snapshot apply base (reset)"
# The restore must have rolled back the mutation: the file must NOT exist now.
assert_exit 1 "mutation is GONE after restore (snapshot is a true reset)" -- \
    "$LINCE_LAB_BIN" --socket "$SOCK" vm exec "$VM" -- test -e "$MUTATION"

ok "01 lima-foundation oracle passed"
exit 0
