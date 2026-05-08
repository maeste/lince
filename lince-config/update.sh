#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DST="$HOME/.local/bin/lince-config"

echo "Updating lince-config..."
cp "$SCRIPT_DIR/lince-config" "$INSTALL_DST"
chmod +x "$INSTALL_DST"
echo "Done. Updated $INSTALL_DST"
