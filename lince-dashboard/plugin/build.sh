#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure rustup toolchain takes precedence over system Rust
export PATH="$HOME/.cargo/bin:$PATH"

TARGET="wasm32-wasip1"
OUTPUT="$SCRIPT_DIR/lince-dashboard.wasm"

# On macOS, verify cargo is rustup-managed — Homebrew's standalone cargo
# cannot see rustup-installed targets (dual Rust installation conflict).
if [ "$(uname -s)" = "Darwin" ]; then
    if ! rustup which cargo >/dev/null 2>&1; then
        echo "ERROR: active cargo is not managed by rustup." >&2
        echo "  Homebrew's standalone cargo cannot build wasm32-wasip1 targets." >&2
        echo "" >&2
        echo "  Fix: ensure the rustup toolchain is set up:" >&2
        echo "    rustup default stable" >&2
        echo "    source ~/.cargo/env" >&2
        echo "" >&2
        echo "  Then verify: rustup which cargo  (should print ~/.cargo/bin/cargo)" >&2
        exit 1
    fi
fi

# Check target
if ! rustup target list --installed 2>/dev/null | grep -q "$TARGET"; then
    echo "Installing $TARGET target..."
    rustup target add "$TARGET"
    if ! rustup target list --installed 2>/dev/null | grep -q "$TARGET"; then
        echo "ERROR: failed to install $TARGET target." >&2
        exit 1
    fi
fi

echo "Building lince-dashboard plugin..."
cargo build --release --target "$TARGET"

# Binary target: output uses hyphens (lince-dashboard), not underscores
ARTIFACT="$SCRIPT_DIR/target/$TARGET/release/lince-dashboard.wasm"
if [ ! -f "$ARTIFACT" ]; then
    echo "ERROR: Build artifact not found at $ARTIFACT" >&2
    exit 1
fi

cp "$ARTIFACT" "$OUTPUT"
SIZE=$(stat --format=%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null)
echo "Built: $OUTPUT ($(( SIZE / 1024 )) KB)"
