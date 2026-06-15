#!/usr/bin/env bash
#
# 00-lib.sh — shared library for the lince-lab CI oracle chain (blueprint §11).
#
# Sourced by every NN-*.sh oracle. Provides:
#   • ANSI color vars (house style, matching scripts/test-vm.sh).
#   • assert helpers (assert / assert_eq / assert_contains / assert_exit /
#     assert_file / assert_no_file) — each prints a labelled PASS/FAIL line and
#     exits non-zero on failure so an oracle's exit is the documented trigger of
#     the next link in the chain.
#   • skip_if_no_kvm — when /dev/kvm is absent OR limactl is not installed,
#     prints 'SKIP: <reason>' and exits 0, so the whole chain is green-or-skipped
#     off a KVM host. VM-dependent oracles call this FIRST; substrate-free checks
#     (09-packaging, the `run validate` portion of 06-recipe) must NOT gate on it.
#
# This file is a library: it is meant to be *sourced*, not executed. It performs
# no actions at source time beyond defining vars + functions.

set -e

# ── color vars (house style) ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── installed-layout paths (install.sh targets; blueprint §1) ────────────────
# Honor XDG_* where the package does, so an isolated-HOME packaging test (09)
# can point everything at a scratch dir and still resolve the same way.
#
# LINCE_LAB_BIN resolution order: an explicit env override always wins; otherwise
# prefer the installed binary, but fall back to the in-repo CLI so substrate-free
# oracles (e.g. 06-recipe Part 1) run on a clean checkout where the module has
# not been installed. This file lives at scripts/lince-lab/ci/, so the module
# tree is three levels up.
if [ -n "${LINCE_LAB_BIN:-}" ]; then
    : # explicit override — honor it verbatim
elif [ -x "$HOME/.local/bin/lince-lab" ]; then
    LINCE_LAB_BIN="$HOME/.local/bin/lince-lab"
else
    _llab_ci_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    LINCE_LAB_BIN="$_llab_ci_lib_dir/../../../lince-lab/lince-lab"
fi
LINCE_LAB_SHARE="${LINCE_LAB_SHARE:-$HOME/.local/share/lince/lince-lab}"
LINCE_LAB_SKILL="${LINCE_LAB_SKILL:-$HOME/.claude/skills/lince-lab}"
LINCE_LAB_CONFIG="${LINCE_LAB_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/lince-lab/config.toml}"
LINCE_LAB_SOCK="${LINCE_LAB_SOCK:-$HOME/.agent-sandbox/lince-lab.sock}"

# ── output helpers ───────────────────────────────────────────────────────────
log() { echo -e "${CYAN}[lince-lab ci]${NC} $*"; }
ok() { echo -e "  ${GREEN}PASS${NC} $*"; }
bad() { echo -e "  ${RED}FAIL${NC} $*" >&2; }

# Announce which oracle is running (call near the top of each NN script).
oracle_header() {
    echo -e "${BOLD}${CYAN}=== $* ===${NC}"
}

# ── skip guard ───────────────────────────────────────────────────────────────
# When the substrate is unavailable, print a SKIP line and exit 0 so the chain
# stays green off a KVM host. VM-dependent oracles call this first; substrate-free
# checks deliberately do not.
skip_if_no_kvm() {
    local reason=""
    if [ ! -e /dev/kvm ]; then
        reason="/dev/kvm not present (no hardware virtualization / not a KVM host)"
    elif ! command -v limactl >/dev/null 2>&1; then
        reason="limactl not installed (Lima backend unavailable)"
    fi
    if [ -n "$reason" ]; then
        echo -e "${YELLOW}SKIP:${NC} $reason"
        exit 0
    fi
    return 0
}

# ── assert helpers ───────────────────────────────────────────────────────────
# Every assert prints a labelled line and exits non-zero on failure. The exit is
# the trigger contract for the chain: an oracle exits 0 only if all asserts pass.

# assert <condition-cmd...> -- <label>
# Runs the given command; PASS if it exits 0, FAIL (exit 1) otherwise.
assert() {
    local label="${*: -1}"
    local cmd=("${@:1:$#-1}")
    if "${cmd[@]}"; then
        ok "$label"
    else
        bad "$label (command failed: ${cmd[*]})"
        exit 1
    fi
}

# assert_eq <actual> <expected> <label>
assert_eq() {
    local actual="$1" expected="$2" label="$3"
    if [ "$actual" = "$expected" ]; then
        ok "$label (= $expected)"
    else
        bad "$label: expected '$expected', got '$actual'"
        exit 1
    fi
}

# assert_exit <expected-code> <label> -- <cmd...>
# Runs <cmd...>, captures its exit code (without set -e aborting), asserts it.
assert_exit() {
    local expected="$1" label="$2"
    shift 2
    [ "$1" = "--" ] && shift
    local code=0
    "$@" || code=$?
    if [ "$code" = "$expected" ]; then
        ok "$label (exit $expected)"
    else
        bad "$label: expected exit $expected, got $code (cmd: $*)"
        exit 1
    fi
}

# assert_contains <haystack> <needle> <label>
assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    case "$haystack" in
        *"$needle"*) ok "$label (contains '$needle')" ;;
        *)
            bad "$label: '$needle' not found in output"
            exit 1
            ;;
    esac
}

# assert_file <path> <label>
assert_file() {
    if [ -e "$1" ]; then
        ok "$2 ($1)"
    else
        bad "$2: $1 does not exist"
        exit 1
    fi
}

# assert_no_file <path> <label>
assert_no_file() {
    if [ ! -e "$1" ]; then
        ok "$2 ($1 absent)"
    else
        bad "$2: $1 still exists"
        exit 1
    fi
}

# ── broker lifecycle helper (shared by VM-dependent oracles) ─────────────────
# Start an in-process broker in the background bound to $1 (socket path), using
# the backend selected by LINCE_LAB_FAKE. Records the PID in BROKER_PID and
# installs a cleanup trap. Waits until the broker answers `lab broker status`.
start_broker() {
    local sock="$1"
    "$LINCE_LAB_BIN" --socket "$sock" lab broker start &
    BROKER_PID=$!
    # shellcheck disable=SC2064
    trap "stop_broker '$sock'" EXIT
    local i=0
    while [ "$i" -lt 50 ]; do
        if "$LINCE_LAB_BIN" --socket "$sock" lab broker status >/dev/null 2>&1; then
            return 0
        fi
        i=$((i + 1))
        # Busy-poll on the broker readiness signal (the socket answering ping),
        # not a fixed sleep of the workload — short backoff only.
        sleep 0.1
    done
    bad "broker did not become reachable on $sock"
    return 1
}

stop_broker() {
    local sock="$1"
    if [ -n "${BROKER_PID:-}" ]; then
        kill "$BROKER_PID" 2>/dev/null || true
        wait "$BROKER_PID" 2>/dev/null || true
        BROKER_PID=""
    fi
    rm -f "$sock" 2>/dev/null || true
}
