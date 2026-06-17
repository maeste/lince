#!/usr/bin/env bash
#
# probe-ht-guest.sh — decisive diagnostic: does `ht` (the shipped host musl
# binary, copied into the guest) actually capture a child program's output into
# its terminal grid when run IN THE GUEST via `limactl shell`?
#
# It boots a throwaway plain Lima VM (no broker, no egress lockdown, none of our
# Python — just limactl + ht), copies ht in, and runs the EXACT invocation the
# broker uses, feeding a {"type":"takeSnapshot"} on stdin. The raw JSONL events
# ht emits are written to a file and then DECODED legibly (no terminal-corrupting
# escape dumps): for each event we print its type, and for grids whether the
# marker is present + the first non-blank rows.
#
# Two variants on the same VM:
#   V1 immediate : sh -c 'echo MARKER; cat'           (the oracle's exact case)
#   V2 delayed   : sh -c 'sleep 1; echo MARKER; cat'  (rules out a startup race)
#
# Needs /dev/kvm + limactl. ~40s (image is already cached from oracle runs).
#
# Usage: bash scripts/lince-lab/ci/probe-ht-guest.sh

set -u

if [ ! -e /dev/kvm ] || ! command -v limactl >/dev/null 2>&1; then
    echo "SKIP: needs /dev/kvm + limactl" >&2
    exit 0
fi

if [ -n "${LINCE_LAB_HT:-}" ]; then
    HT="$LINCE_LAB_HT"
else
    HT="${XDG_DATA_HOME:-$HOME/.local/share}/lince/lince-lab/bin/ht"
fi
[ -x "$HT" ] || { echo "ERROR: ht not found at $HT" >&2; exit 1; }

VM="lince-lab-htprobe-$$"
MARKER="GUESTPROBEMARKER"
OUT_DIR="$(mktemp -d)"

cleanup() {
    limactl delete -f "$VM" >/dev/null 2>&1 || true
    rm -rf "$OUT_DIR"
}
trap cleanup EXIT

echo "=== ht guest-render probe ==="
echo "ht: $HT   vm: $VM"

echo "--- creating + starting a throwaway plain VM (image is cached) ---"
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
limactl copy "$HT" "$VM":/tmp/htp >/dev/null 2>&1
limactl shell "$VM" -- chmod +x /tmp/htp >/dev/null 2>&1
echo "VM up; ht copied to /tmp/htp"

# run_variant LABEL -- PROG ARG...   (PROG ARG... is the raw program argv ht wraps)
run_variant() {
    local label="$1"; shift
    [ "$1" = "--" ] && shift
    local out="$OUT_DIR/$label.jsonl"
    echo ""
    echo "──────────────────────────────────────────────────────────────"
    echo "VARIANT $label : program argv = [$*]"
    echo "──────────────────────────────────────────────────────────────"
    # Feed a takeSnapshot at +3s while the program is alive; keep stdin open.
    { sleep 3; printf '%s\n' '{"type":"takeSnapshot"}'; sleep 3; } \
      | timeout 20 limactl shell "$VM" -- /tmp/htp --size 80x24 \
            --subscribe init,output,snapshot -- "$@" \
      > "$out" 2>"$OUT_DIR/$label.err" || true

    if [ -s "$OUT_DIR/$1.err" ]; then
        echo "ht stderr:"; sed 's/^/   /' "$OUT_DIR/$1.err"
    fi
    echo "raw events: $(wc -l < "$out") line(s). Decoded:"
    python3 - "$out" "$MARKER" <<'PY'
import json, sys
path, marker = sys.argv[1], sys.argv[2]
n = 0
with open(path, errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            ev = json.loads(line)
        except Exception:
            print(f"   NONJSON: {line[:90]!r}")
            continue
        t = ev.get("type")
        d = ev.get("data") if isinstance(ev.get("data"), dict) else {}
        if t == "output":
            seq = d.get("seq", "") if isinstance(d, dict) else str(ev.get("data"))
            print(f"   output   seq={seq!r}")
        elif t in ("init", "snapshot"):
            text = d.get("text", "") or ""
            rows = [r.rstrip() for r in text.split("\n")]
            nonblank = [r for r in rows if r.strip()]
            has = marker in text
            print(f"   {t:8} {d.get('cols')}x{d.get('rows')} marker={'YES' if has else 'no'} "
                  f"nonblank_rows={nonblank[:3]}")
        else:
            print(f"   {t}: {str(ev.get('data'))[:80]}")
if n == 0:
    print("   (no events at all — ht emitted nothing)")
PY
}

# The FIX candidate: a simple single-word argv (no spaces in any element, no shell
# metacharacters) survives `limactl shell`. `yes MARKER` floods the marker and
# stays alive — this is what the oracle should use.
run_variant "yes"           -- yes "$MARKER"
# For contrast: the OLD broken form — a single arg with spaces gets word-split by
# the limactl transport, so ht runs a mangled command and the grid is wrong.
run_variant "sh-c-multiword" -- sh -c "echo $MARKER; cat"

echo ""
echo "=== verdict ==="
echo "• VARIANT 'yes' snapshot marker=YES  → the fix works: drive the oracle with"
echo "  'yes <marker>' (simple argv survives limactl shell). Re-run oracle 05."
echo "• VARIANT 'sh-c-multiword' marker=no  → confirms the limactl word-split: a"
echo "  space-containing argv element does not survive (that was the bug)."
