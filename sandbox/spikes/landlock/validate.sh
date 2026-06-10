#!/usr/bin/env bash
# Landlock spike validation runner (#211 / #222).
# Paste-proof wrapper around the four spike checks so a wrapping terminal
# cannot split a long bwrap argv across newlines. Run from the repo root:
#
#   sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0   # Ubuntu 24.04+: unblock unpriv userns
#   bash sandbox/spikes/landlock/validate.sh
#
# Writes a transcript to /tmp/landlock-validation.log. Never aborts on a
# single failing step — each step's exit code is reported so a partial
# environment still produces a useful record.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=/tmp/landlock-validation.log

run() {  # run "<label>" <cmd...>
  local label="$1"; shift
  echo "--- ${label}"
  "$@"
  echo "    rc=$?"
  echo
}

{
  echo "=== HOST: $(uname -r) | $( . /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-unknown}") ==="
  echo "=== unpriv userns sysctl: $(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || echo n/a) (0 = allowed)"
  echo

  run "[1/5] probe"                  python3 "${HERE}/landlock_probe.py"
  run "[2/5] demo (fs+net+inherit)"  python3 "${HERE}/demo.py"
  # Re-bind the spike dir INTO the fresh tmpfs (writable, so bwrap can make the
  # mountpoint) so --tmpfs /tmp does not shadow it when the repo is under /tmp.
  run "[3/5] Q4: demo under bwrap"   bwrap --ro-bind / / --tmpfs /tmp --dev /dev --proc /proc --ro-bind "${HERE}" /tmp/spike -- python3 /tmp/spike/demo.py
  run "[4/5] paranoid gate (native ABI)" bash "${HERE}/paranoid_gate.sh"
  echo "--- [5/5] paranoid gate (FORCE_ABI=4 — exercises the v4 codepath)"
  LINCE_LANDLOCK_FORCE_ABI=4 bash "${HERE}/paranoid_gate.sh"
  echo "    rc=$?"
  echo
  echo "=== DONE — transcript at ${LOG} ==="
} 2>&1 | tee "${LOG}"
