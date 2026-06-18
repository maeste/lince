#!/usr/bin/env bash
#
# clean.sh — tear down all lince-lab lab VMs + the broker, for a clean slate.
#
# Failed/interrupted oracle runs can leave `lince-lab-*` Lima instances and a
# stray broker behind (their cleanup trap never fired). This removes them.
#
# SAFE: it only ever touches the `lince-lab-` instance namespace and the
# lince-lab broker socket/process — never your other Lima VMs.
#
# Usage: bash scripts/lince-lab/ci/clean.sh

set -u

PREFIX="lince-lab-"
SOCK="${LINCE_LAB_SOCK:-$HOME/.agent-sandbox/lince-lab.sock}"

if command -v limactl >/dev/null 2>&1; then
    # `limactl list -q` prints one instance name per line; force-delete handles
    # running instances. Grep keeps us strictly inside the lince-lab- namespace.
    mapfile -t vms < <(limactl list -q 2>/dev/null | grep "^${PREFIX}" || true)
    if [ "${#vms[@]}" -eq 0 ]; then
        echo "No lince-lab-* instances to delete."
    else
        for vm in "${vms[@]}"; do
            echo "deleting $vm"
            limactl delete -f "$vm" || echo "  (delete failed for $vm — continuing)"
        done
    fi
else
    echo "limactl not found; no VMs to delete."
fi

# Stop any lingering in-process broker and drop its socket.
pkill -f "lince-lab.* lab broker start" 2>/dev/null && echo "stopped a lingering broker" || true
rm -f "$SOCK" 2>/dev/null && echo "removed $SOCK" || true

echo "clean: done."
