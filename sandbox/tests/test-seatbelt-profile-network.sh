#!/usr/bin/env bash
# test-seatbelt-profile-network.sh — Seatbelt paranoid network containment (#196)
#
# Enforced rules:
#   1. generate_seatbelt_profile(paranoid) emits (deny network*) + loopback-only
#      allows and does NOT emit the broad (allow network*).
#   2. Base (normal) and permissive profiles keep (allow network*) and contain
#      no (deny network*).
#   3. The seatbelt run path computes enforce_allowlist with the exact same
#      expression as the bwrap path: bool(sec.get("unshare_net", False)).
#   4. CredentialProxy with enforce_allowlist=True rejects CONNECT to a
#      non-allowed host with 403, allows an allow_domains host, and always
#      blocks metadata endpoints (403).
#
# Pure host-side test: runs on Linux, no macOS / sandbox-exec required.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGENT_SANDBOX="$REPO_ROOT/sandbox/agent-sandbox"

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "ok: $*"; }

[ -f "$AGENT_SANDBOX" ] || fail "agent-sandbox not found at $AGENT_SANDBOX"

# --- Rule 3: enforce_allowlist parity (textual, both backends) ---------------
count=$(grep -c 'enforce_allowlist = bool(sec.get("unshare_net", False))' "$AGENT_SANDBOX")
if [ "$count" -ne 2 ]; then
    fail "expected enforce_allowlist = bool(sec.get(\"unshare_net\", False)) on both bwrap and seatbelt paths (found $count occurrence(s))"
fi
pass "enforce_allowlist parity expression present on both backend paths"

# --- Rules 1, 2, 4: profile generation + proxy behavior (python) -------------
python3 - "$AGENT_SANDBOX" <<'EOF'
import socket
import sys
import tempfile
import threading
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

spec = spec_from_loader("agent_sandbox", SourceFileLoader("agent_sandbox", sys.argv[1]))
m = module_from_spec(spec)
spec.loader.exec_module(m)

# --- Profile generation -------------------------------------------------
para, _ = m.generate_seatbelt_profile("claude", {}, {}, sandbox_level="paranoid")
base, _ = m.generate_seatbelt_profile("claude", {}, {})
perm, _ = m.generate_seatbelt_profile("claude", {}, {}, sandbox_level="permissive")

assert "(deny network*)" in para, "paranoid profile missing (deny network*)"
assert "(allow network*)" not in para, "paranoid profile must not contain broad (allow network*)"
assert '(allow network-outbound (remote ip "localhost:*"))' in para, "paranoid missing loopback outbound allow"
assert '(allow network-inbound (local ip "localhost:*"))' in para, "paranoid missing loopback inbound allow"
assert '(allow network-bind (local ip "localhost:*"))' in para, "paranoid missing loopback bind allow"
print("ok: paranoid profile is loopback-only (deny network* + loopback allows)")

for name, text in (("base", base), ("permissive", perm)):
    assert "(allow network*)" in text, f"{name} profile missing (allow network*)"
    assert "(deny network*)" not in text, f"{name} profile must not contain (deny network*)"
print("ok: base and permissive profiles keep broad (allow network*)")

# --- CredentialProxy enforce_allowlist behavior -------------------------
# Keep the proxy PID file out of ~/.agent-sandbox during the test.
tmpdir = tempfile.mkdtemp(prefix="lince-sb-test-")
m.SANDBOX_DIR = Path(tmpdir)

rule = {
    "domain": "api.anthropic.com",
    "header_name": "x-api-key",
    "header_value": "test-key",
    "base_url_env": "ANTHROPIC_BASE_URL",
    "upstream_base": "https://api.anthropic.com",
}
proxy = m.CredentialProxy(
    [rule],
    allow_domains=["127.0.0.1"],
    enforce_allowlist=True,
)
port = proxy.start()


def connect_status(host_port: str) -> str:
    """Send a CONNECT for *host_port* through the proxy, return the status line."""
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    try:
        s.sendall(
            f"CONNECT {host_port} HTTP/1.1\r\nHost: {host_port}\r\n\r\n".encode()
        )
        return s.recv(4096).decode("utf-8", "replace").splitlines()[0]
    finally:
        s.close()


# Local upstream listener so the allowed-host CONNECT succeeds offline.
upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
upstream.bind(("127.0.0.1", 0))
upstream.listen(1)
up_port = upstream.getsockname()[1]
threading.Thread(target=lambda: upstream.accept(), daemon=True).start()

try:
    status = connect_status("evil.example:443")
    assert " 403 " in status, f"non-allowed host: expected 403, got: {status}"
    print("ok: CONNECT to non-allowed host rejected with 403")

    status = connect_status("169.254.169.254:443")
    assert " 403 " in status, f"metadata endpoint: expected 403, got: {status}"
    print("ok: CONNECT to metadata endpoint blocked with 403")

    status = connect_status(f"127.0.0.1:{up_port}")
    assert " 200 " in status, f"allow_domains host: expected 200, got: {status}"
    print("ok: CONNECT to allow_domains host tunneled (200)")
finally:
    proxy.stop()
    upstream.close()
EOF
rc=$?
if [ "$rc" -ne 0 ]; then
    fail "python assertions failed (exit $rc)"
fi

echo "All seatbelt paranoid network tests passed."
exit 0
