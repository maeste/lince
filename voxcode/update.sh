#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/voxcode"
CONFIG_DST="$CONFIG_DIR/config.toml"
CONFIG_SRC="$SCRIPT_DIR/config.example.toml"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   VoxCode — Update${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv not found. Run install.sh first."
    exit 1
fi

# ── Step 1: Update binary ────────────────────────────────────────────
echo -e "${GREEN}[1/2] Updating voxcode...${NC}"
uv tool install --from "$SCRIPT_DIR" --force --reinstall voxcode 2>&1 | while read -r line; do
    echo "  $line"
done

echo -e "${GREEN}  ✓ Updated: $(command -v voxcode 2>/dev/null || echo '~/.local/bin/voxcode')${NC}"
echo ""

# ── Step 2: Update config (add missing keys, keep user values) ───────
echo -e "${GREEN}[2/2] Checking configuration...${NC}"

mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DST" ]; then
    # No config at all — install fresh
    cp "$CONFIG_SRC" "$CONFIG_DST"
    echo -e "${GREEN}  ✓ Installed new config: $CONFIG_DST${NC}"
elif [ -f "$CONFIG_SRC" ]; then
    # Config exists — check for new sections/keys in example that are
    # missing from the user's file, and append them as comments.
    added=0
    while IFS= read -r line; do
        # Track current section
        if [[ "$line" =~ ^\[([a-z_]+)\] ]]; then
            section="${BASH_REMATCH[1]}"
            if ! grep -q "^\[${section}\]" "$CONFIG_DST" 2>/dev/null; then
                echo "" >> "$CONFIG_DST"
                echo "$line" >> "$CONFIG_DST"
                echo -e "${YELLOW}  + Added new section: [$section]${NC}"
                added=$((added + 1))
            fi
        fi
    done < "$CONFIG_SRC"

    if [ "$added" -eq 0 ]; then
        echo -e "${GREEN}  ✓ Config up to date: $CONFIG_DST${NC}"
    fi
else
    echo -e "${GREEN}  ✓ Config present: $CONFIG_DST${NC}"
fi
echo ""

echo -e "${GREEN}Update complete.${NC}"
echo ""
