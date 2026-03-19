#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure rustup toolchain takes precedence over system Rust
export PATH="$HOME/.cargo/bin:$PATH"

TARGET="wasm32-wasip1"
OUTPUT="$SCRIPT_DIR/lince-dashboard.wasm"

# Check target
if ! rustup target list --installed 2>/dev/null | grep -q "$TARGET"; then
    echo "Installing $TARGET target..."
    rustup target add "$TARGET"
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
