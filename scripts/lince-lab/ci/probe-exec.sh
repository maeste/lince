#!/usr/bin/env bash
#
# probe-exec.sh — does `limactl shell VM -- sh -c '<multi-word script>'` preserve
# the script as a SINGLE argument, or does the transport re-split/re-parse it?
#
# This is the foundation recipe steps stand on: a step like
#   run = ["sh", "-c", "cd /work && npm install ..."]
# becomes `limactl shell VM -- sh -c "cd /work && npm install ..."`. If the
# transport mangles the multi-word `-c` script (as it did for the ht capture
# program — see probe-ht-guest.sh), recipe steps break.
#
# Boots a throwaway plain VM and runs a few exec forms, printing exact output so
# the behavior is unambiguous. Needs /dev/kvm + limactl. ~40s (image cached).
#
# Usage: bash scripts/lince-lab/ci/probe-exec.sh

set -u

if [ ! -e /dev/kvm ] || ! command -v limactl >/dev/null 2>&1; then
    echo "SKIP: needs /dev/kvm + limactl" >&2
    exit 0
fi

VM="lince-lab-execprobe-$$"
cleanup() { limactl delete -f "$VM" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "=== limactl shell exec probe ===  vm: $VM"
echo "--- creating + starting a throwaway plain VM (image cached) ---"
limactl create --name "$VM" - >/dev/null 2>&1 <<'YAML'
images:
- location: "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
  arch: "x86_64"
  digest: "sha256:28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f"
cpus: 2
memory: "2GiB"
disk: "20GiB"
plain: true
mounts: []
YAML
limactl start "$VM" >/dev/null 2>&1 || { echo "ERROR: VM failed to start" >&2; exit 1; }
echo "VM up."

run() {
    local label="$1"; shift
    echo ""
    echo "── $label"
    echo "   argv: limactl shell $VM -- $*"
    echo "   output (between <<< >>>):"
    printf '   <<<'
    limactl shell "$VM" -- "$@" 2>&1 | sed 's/^/   /'
    printf '   >>> (exit %s)\n' "$?"
}

# 1) The critical case: a multi-word `sh -c` script with `;` and `&&`.
run "multi-word sh -c with ; and &&" sh -c 'echo AA BB; cd /tmp && echo PWD=$(pwd)'
#    EXPECT: a line "AA BB" then "PWD=/tmp". If you see "AA" split from "BB", or
#    pwd is /home (not /tmp), or "missing operand"-type errors → the script was
#    mangled by the transport and recipe steps need a transport fix.

# 2) The exact shape of the failing recipe step.
run "recipe-step shape (cd + &&)" sh -c 'mkdir -p /tmp/ep && cd /tmp/ep && pwd && echo STEP-OK'
#    EXPECT: "/tmp/ep" then "STEP-OK".

# 3) Simple single-word argv (should always be fine) — the sudo pre-create form.
run "sudo mkdir + chmod (single-word argv)" sudo mkdir -p /work
run "ls the sudo-made dir" ls -ld /work

echo ""
echo "=== verdict ==="
echo "• Tests 1 & 2 print the expected lines (AA BB / PWD=/tmp / STEP-OK) → multi-word"
echo "  sh -c survives; recipe steps are fine."
echo "• They show split words, wrong pwd, or operand errors → backend.exec needs a"
echo "  transport fix (shell-quote the remote command). Paste this whole block."
