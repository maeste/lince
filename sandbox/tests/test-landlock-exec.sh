#!/usr/bin/env bash
# Landlock enforcement gate for `agent-sandbox __landlock-exec` (#222).
# Ports the #211 spike's gate assertions against the PRODUCTION shim.
# Needs a Landlock-capable kernel (ABI >= 1); net checks need ABI >= 4
# and are skipped below that. Run:  bash sandbox/tests/test-landlock-exec.sh
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX="$SCRIPT_DIR/../agent-sandbox"
WORK="$(mktemp -d /tmp/lince-landlock-test.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
ok()   { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
bad()  { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

ABI=$(python3 - <<EOF
import importlib.util, importlib.machinery
spec = importlib.util.spec_from_loader("a", importlib.machinery.SourceFileLoader("a", "$SANDBOX"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.probe_landlock_abi())
EOF
)
echo "Landlock ABI: $ABI"
if [ "$ABI" -lt 1 ]; then
    echo "SKIP: kernel has no Landlock — only the degraded paths can be tested."
fi

# ── 1. fs fence: write inside rw allowed, outside denied ─────────────────
if [ "$ABI" -ge 1 ]; then
    mkdir -p "$WORK/inside"
    OUT=$(python3 "$SANDBOX" __landlock-exec --rw "$WORK/inside" -- python3 -c "
try:
    open('$WORK/inside/f', 'w').write('x'); print('IN_OK')
except PermissionError: print('IN_DENIED')
try:
    open('$WORK/outside', 'w'); print('OUT_OK')
except PermissionError: print('OUT_DENIED')
" 2>/dev/null)
    echo "$OUT" | grep -q IN_OK && ok "fs: write inside rw path succeeds" \
                                || bad "fs: write inside rw path ($OUT)"
    echo "$OUT" | grep -q OUT_DENIED && ok "fs: write outside rw path denied" \
                                      || bad "fs: write outside rw path NOT denied ($OUT)"

    # ── 2. inheritance: fence survives fork+execve ──────────────────────
    OUT=$(python3 "$SANDBOX" __landlock-exec --rw "$WORK/inside" -- bash -c "
python3 -c \"open('$WORK/outside2','w')\" 2>/dev/null && echo CHILD_OUT_OK || echo CHILD_OUT_DENIED")
    echo "$OUT" | grep -q CHILD_OUT_DENIED && ok "inherit: subprocess still fenced" \
                                            || bad "inherit: subprocess escaped the fence ($OUT)"
fi

# ── 3. net rules (ABI >= 4): connect allowed port only, bind denied ──────
if [ "$ABI" -ge 4 ]; then
    OUT=$(python3 - "$SANDBOX" <<'EOF'
import socket, subprocess, sys
sandbox = sys.argv[1]
l1, l2 = socket.socket(), socket.socket()
l1.bind(("127.0.0.1", 0)); l1.listen(1)
l2.bind(("127.0.0.1", 0)); l2.listen(1)
allowed, denied = l1.getsockname()[1], l2.getsockname()[1]
code = f"""
import socket, errno
for port, want in (({allowed}, "ALLOWED"), ({denied}, "DENIED")):
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect(("127.0.0.1", port)); print(f"CONNECT_{{want}}_OK")
    except PermissionError: print(f"CONNECT_{{want}}_EACCES")
    finally: s.close()
b = socket.socket()
try:
    b.bind(("127.0.0.1", 0)); print("BIND_OK")
except PermissionError: print("BIND_EACCES")
"""
print(subprocess.run(
    ["python3", sandbox, "__landlock-exec", "--rw", "/tmp",
     "--connect-port", str(allowed), "--", "python3", "-c", code],
    capture_output=True, text=True).stdout)
EOF
)
    echo "$OUT" | grep -q CONNECT_ALLOWED_OK && ok "net: connect to allowed port succeeds" \
                                              || bad "net: connect to allowed port failed ($OUT)"
    echo "$OUT" | grep -q CONNECT_DENIED_EACCES && ok "net: connect to other port denied" \
                                                 || bad "net: connect to other port NOT denied ($OUT)"
    echo "$OUT" | grep -q BIND_EACCES && ok "net: bind denied (no bind rule)" \
                                       || bad "net: bind NOT denied ($OUT)"
else
    echo "  [SKIP] net checks (ABI $ABI < 4)"
fi

# ── 4. degraded paths (simulated old kernel) ─────────────────────────────
LINCE_LANDLOCK_FORCE_ABI=0 python3 "$SANDBOX" __landlock-exec --rw /tmp -- true 2>/dev/null
[ $? -eq 0 ] && ok "ABI 0 graceful: agent still execs (bwrap-only containment)" \
             || bad "ABI 0 graceful path broke the launch"

LINCE_LANDLOCK_FORCE_ABI=0 python3 "$SANDBOX" __landlock-exec --fail-closed --rw /tmp -- true 2>/dev/null
[ $? -eq 1 ] && ok "ABI 0 + --fail-closed: refuses to exec (I7)" \
             || bad "ABI 0 + --fail-closed did NOT fail closed"

if [ "$ABI" -ge 4 ]; then
    LINCE_LANDLOCK_FORCE_ABI=3 python3 "$SANDBOX" __landlock-exec --fail-closed \
        --rw /tmp --connect-port 1234 -- true 2>/dev/null
    [ $? -eq 1 ] && ok "ABI 3 + net requested + --fail-closed: refuses to exec (I7)" \
                 || bad "ABI 3 net degradation did NOT fail closed"
fi

# ── 5. record merge: shim writes ground truth into the #221 record ───────
REC="$WORK/rec.policy.json"
echo '{"schema":1,"backend":"bwrap","inherited_by_subprocesses":"by-design"}' > "$REC"
if [ "$ABI" -ge 1 ]; then
    LINCE_POLICY_RECORD_PATH="$REC" python3 "$SANDBOX" __landlock-exec \
        --rw /tmp --rw "$WORK" -- true 2>/dev/null
    python3 - "$REC" <<'EOF' && ok "record: shim merged landlock ground truth" || bad "record: shim did not update the record"
import json, sys
r = json.load(open(sys.argv[1]))
assert r["backend"] == "bwrap"            # host fields preserved
assert r["landlock_abi"] >= 1
assert r["fs_enforced"] is True
assert r["applied_before_exec"] is True
assert "verified" in r["inherited_by_subprocesses"]
EOF
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "LANDLOCK GATE: ALL $PASS CHECKS PASSED"
    exit 0
else
    echo "LANDLOCK GATE: $FAIL FAILED, $PASS passed"
    exit 1
fi
