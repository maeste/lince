#!/usr/bin/env bash
set -e

INSTALL_DST="$HOME/.local/bin/lince-config"

if [ -f "$INSTALL_DST" ]; then
    rm "$INSTALL_DST"
    echo "Removed $INSTALL_DST"
else
    echo "lince-config is not installed."
fi
