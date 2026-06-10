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
#      paranoid sandbox (see its docstring), exit 0 = all pass.
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
EOF

cd "$PROJ"
python3 "$REPO/sandbox/agent-sandbox" run -a landlock-demo \
  --sandbox-level paranoid -p "$PROJ" -- \
  --rw "$PROJ" --connect-port 8118 -- \
  python3 "$PROJ/gate_check.py" "$PROJ"
