#!/usr/bin/env bash
# Paranoid Landlock gate prototype (#211) — gates one agent at
# `--sandbox-level paranoid` through the landlock_exec.py shim, using
# ONLY existing agent-sandbox mechanisms (project-local config + custom
# agent command). agent-sandbox itself is NOT modified.
#
# What it does:
#   1. creates a throwaway project dir with a project-local
#      .agent-sandbox/config.toml defining agent `landlock-demo` whose
#      command IS the shim, plus a project-local paranoid fragment
#      (credential_proxy + unshare_net, same [security] as shipped
#      paranoid levels);
#   2. runs `agent-sandbox run -a landlock-demo --sandbox-level paranoid`
#      so the chain is exactly the design doc's Option B:
#      unshare/socat wrapper -> bwrap <mounts> -> landlock_exec.py
#      (rw=project, connect=8118) -> gate_check.py assertions;
#   3. gate_check.py proves fs + net fences hold inside the real
#      paranoid sandbox (see its docstring), exit 0 = all pass;
#   4. captures the shim's LINCE_EFFECTIVE_POLICY record from the gated
#      run and asserts fs_enforced=true, net_enforced=true,
#      net_limitation="port-only, host-unaware" (#211, rpelevin).
#
# Run from anywhere:  bash sandbox/spikes/landlock/paranoid_gate.sh
set -euo pipefail

SPIKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SPIKE_DIR/../../.." && pwd)"

PROJ="$(mktemp -d /tmp/landlock_gate_XXXXXX)"
trap 'rm -rf "$PROJ"' EXIT

# The repo may live under $HOME, which paranoid covers with tmpfs — copy
# the shim and the check payload into the project dir (bind-mounted rw
# into the sandbox at the same path) so they are visible inside.
cp "$SPIKE_DIR/landlock_exec.py" "$SPIKE_DIR/gate_check.py" "$PROJ/"
chmod +x "$PROJ/landlock_exec.py"

mkdir -p "$PROJ/.agent-sandbox/profiles" "$PROJ/.agent-sandbox/claude-config"
cat > "$PROJ/.agent-sandbox/config.toml" <<EOF
# Gate the landlock-demo agent through the Landlock shim (#211).
[agents.landlock-demo]
command = "$PROJ/landlock_exec.py"
default_args = []

[claude]
# Keep the default ~/.agent-sandbox/claude-config bind out of the picture:
# the gate must not depend on (or touch) the user's sandbox install.
config_dir = "$PROJ/.agent-sandbox/claude-config"
EOF
cat > "$PROJ/.agent-sandbox/profiles/landlock-demo-paranoid.toml" <<'EOF'
# Paranoid fragment for the gate prototype: same [security] semantics as
# the shipped <agent>-paranoid levels (fresh netns + credential proxy
# reached via the in-sandbox socat bridge on 127.0.0.1:8118).
[security]
credential_proxy = true
unshare_net = true
allow_domains = []

[env.extra]
# Dummy credential so the proxy has a rule and the socat bridge is live;
# never sent anywhere (gate_check only TCP-connects to the bridge).
ANTHROPIC_API_KEY = "sk-test-landlock-spike"
# Launch context for the shim's effective-policy record (#211): in
# production agent-sandbox itself would export these (#221).
LINCE_SANDBOX_LEVEL = "paranoid"
EOF

cd "$PROJ"
LOG="$PROJ/gate.log"
python3 "$REPO/sandbox/agent-sandbox" run -a landlock-demo \
  --sandbox-level paranoid -p "$PROJ" -- \
  --rw "$PROJ" --connect-port 8118 -- \
  python3 "$PROJ/gate_check.py" "$PROJ" 2>&1 | tee "$LOG"

# --- Effective-policy record: capture + assert (#211, rpelevin) ----------
RECORD_LINE="$(grep -m1 'LINCE_EFFECTIVE_POLICY: ' "$LOG" || true)"
if [[ -z "$RECORD_LINE" ]]; then
  echo "gate: FAIL — no LINCE_EFFECTIVE_POLICY record in gated run output" >&2
  exit 1
fi
echo
echo "gate: effective-policy record from the gated run:"
echo "  $RECORD_LINE"
python3 - "${RECORD_LINE#*LINCE_EFFECTIVE_POLICY: }" <<'PY'
import json
import sys

rec = json.loads(sys.argv[1])
want = {
    "fs_enforced": True,
    "net_enforced": True,
    "net_limitation": "port-only, host-unaware",
}
bad = {k: rec.get(k) for k, v in want.items() if rec.get(k) != v}
if bad:
    print(f"gate: FAIL — record assertions: {bad}", file=sys.stderr)
    sys.exit(1)
print('gate: record asserts fs_enforced=true, net_enforced=true, '
      'net_limitation="port-only, host-unaware" — OK')
PY
