#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX_CMD="$SCRIPT_DIR/claude-sandbox"
INSTALL_DST="$HOME/.local/bin/claude-sandbox"
CONFIG_DST="$HOME/.claude-sandbox/config.toml"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   claude-sandbox — Update${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# ── Step 1: Update command ─────────────────────────────────────────────
echo -e "${GREEN}[1/2] Updating claude-sandbox command...${NC}"

if [ ! -f "$INSTALL_DST" ]; then
    echo -e "${YELLOW}  Not installed — run install.sh first${NC}"
    exit 1
fi

cp "$SANDBOX_CMD" "$INSTALL_DST"
chmod +x "$INSTALL_DST"
echo -e "${GREEN}  ✓ Command updated${NC}"
echo ""

# ── Step 2: Ensure env passthrough ─────────────────────────────────────
echo -e "${GREEN}[2/2] Checking env passthrough...${NC}"

# Required vars for lince-dashboard integration and terminal tools
REQUIRED_VARS=("ZELLIJ" "ZELLIJ_SESSION_NAME" "LINCE_AGENT_ID")

if [ ! -f "$CONFIG_DST" ]; then
    echo -e "${YELLOW}  No config found — run install.sh first${NC}"
    echo ""
    echo -e "${GREEN}Update complete (command only).${NC}"
    exit 0
fi

# Check which vars are missing from passthrough
MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if ! python3 -c "
import tomllib, sys
with open(sys.argv[1], 'rb') as f:
    cfg = tomllib.load(f)
sys.exit(0 if sys.argv[2] in cfg.get('env', {}).get('passthrough', []) else 1)
" "$CONFIG_DST" "$var" 2>/dev/null; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo -e "${GREEN}  ✓ Passthrough already configured${NC}"
else
    echo -e "${YELLOW}  Adding env passthrough for: ${MISSING_VARS[*]}${NC}"

    # Pass missing vars as arguments to Python
    python3 - "$CONFIG_DST" "${MISSING_VARS[@]}" << 'PYEOF'
import tomllib, sys, re

config_path = sys.argv[1]
missing = sys.argv[2:]

with open(config_path, "rb") as f:
    cfg = tomllib.load(f)

existing = list(cfg.get("env", {}).get("passthrough", []))
new_list = existing + [v for v in missing if v not in existing]
vals = ", ".join(f'"{v}"' for v in new_list)
new_line = f"passthrough = [{vals}]"

with open(config_path) as f:
    content = f.read()

if "passthrough" in content:
    content = re.sub(r'passthrough\s*=\s*\[.*?\]', new_line, content, flags=re.DOTALL)
elif "[env]" in content:
    content = content.replace("[env]", f"[env]\n{new_line}")
else:
    content += f"\n[env]\n{new_line}\n"

with open(config_path, "w") as f:
    f.write(content)
PYEOF

    echo -e "${GREEN}  ✓ Passthrough updated${NC}"
fi
echo ""

echo -e "${GREEN}Update complete.${NC}"
echo ""
