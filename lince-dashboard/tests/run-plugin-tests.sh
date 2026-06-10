#!/usr/bin/env bash
# Run the dashboard plugin's Rust unit tests.
#
# `cargo test` on the host target fails to link (the zellij host imports only
# exist inside the Zellij runtime), so the suite is built for wasm32-wasip1
# and run under wasmtime with a no-op stub of the host interface
# (zellij-host-stub.wat). Same recipe as PR #226's validation.
#
# Requirements: rustup toolchain with the wasm32-wasip1 target, wasmtime.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$SCRIPT_DIR/../plugin"
STUB="$SCRIPT_DIR/zellij-host-stub.wat"

command -v wasmtime >/dev/null 2>&1 || {
    echo "error: wasmtime not found (brew install wasmtime / dnf install wasmtime)" >&2
    exit 1
}

CARGO="$HOME/.cargo/bin/cargo"
[ -x "$CARGO" ] || CARGO="cargo"

cd "$PLUGIN_DIR"
PATH="$HOME/.cargo/bin:$PATH" "$CARGO" test --target wasm32-wasip1 --no-run

WASM="$(ls -t target/wasm32-wasip1/debug/deps/lince_dashboard-*.wasm | head -1)"
[ -n "$WASM" ] || { echo "error: no test artifact found" >&2; exit 1; }

# NOTE: tests are built with panic=abort on wasm, so the run stops at the
# first failing test. Re-run with a name filter to isolate failures:
#   wasmtime run --preload zellij=<stub> <wasm> <test_name_substring>
exec wasmtime run --preload "zellij=$STUB" "$WASM" "$@"
