#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   VoxCode — Update${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv not found. Run install.sh first."
    exit 1
fi

echo -e "${GREEN}[1/1] Updating voxcode...${NC}"
uv tool install --from "$SCRIPT_DIR" --force --reinstall voxcode 2>&1 | while read -r line; do
    echo "  $line"
done

echo -e "${GREEN}  ✓ Updated: $(command -v voxcode 2>/dev/null || echo '~/.local/bin/voxcode')${NC}"
echo ""
echo -e "${GREEN}Update complete.${NC}"
echo ""
