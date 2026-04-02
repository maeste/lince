# Quickstart.sh — prerequisite and UX fixes

## 1. Fix rustc → rustup prerequisite check (check_prerequisites, ~line 590)

Current:
```bash
# Rust (for WASM build)
if command -v rustc >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} rustc $(rustc --version 2>/dev/null | awk '{print $2}')"
else
    warnings+=("Rust not found (required to build dashboard plugin)")
    echo -e "  ${YELLOW}✗${NC} rustc not found — needed to build dashboard"
fi
```

Replace with:
```bash
# Rustup (distro rustc alone cannot provide wasm32 targets needed for dashboard)
if command -v rustup >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} rustup $(rustup --version 2>/dev/null | awk '{print $2}')"
else
    warnings+=("rustup not found (required to build dashboard WASM plugin)")
    echo -e "  ${YELLOW}✗${NC} rustup not found — needed to build dashboard"
    echo -e "      ${DIM}Install: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | RUSTUP_INIT_SKIP_PATH_CHECK=yes sh${NC}"
fi
```

Why: distro `rustc` can't compile WASM (no wasm32 stdlib). Only `rustup` can provide it. The `RUSTUP_INIT_SKIP_PATH_CHECK=yes` env var must be on the `sh` side of the pipe (not `curl` side) — it skips the "existing Rust in PATH" check that blocks installation when distro rustc exists.

## 2. Add jq and Node.js prerequisite checks (check_prerequisites, after existing checks)

Add these checks in the check_prerequisites function:

```bash
# jq
if command -v jq >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} jq"
else
    warnings+=("jq not found")
    echo -e "  ${YELLOW}✗${NC} jq not found"
    if [ "$OS_NAME" = "Darwin" ]; then
        echo -e "      ${DIM}Install: brew install jq${NC}"
    else
        echo -e "      ${DIM}# Fedora/RHEL: sudo dnf install jq${NC}"
        echo -e "      ${DIM}# Ubuntu/Debian: sudo apt install jq${NC}"
    fi
fi

# Node.js
if command -v node >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} node $(node --version 2>/dev/null)"
else
    warnings+=("Node.js not found")
    echo -e "  ${YELLOW}✗${NC} node not found"
    if [ "$OS_NAME" = "Darwin" ]; then
        echo -e "      ${DIM}Install: brew install node${NC}"
    else
        echo -e "      ${DIM}# Fedora/RHEL: sudo dnf install nodejs${NC}"
        echo -e "      ${DIM}# Ubuntu/Debian: sudo apt install nodejs${NC}"
    fi
fi
```

## 3. Add Python install suggestions (check_prerequisites, existing Python check)

The existing Python check reports missing but gives no install hint. Add install suggestions matching the pattern above (brew on macOS, dnf/apt on Linux) for both "too old" and "not found" cases. Use `python3.11` as the package name.

## 4. Skip VoxCode on macOS (main flow, ~line 762)

Current:
```bash
    select_backends
    select_agents
    select_voxcode
    confirm_installation
```

Replace with:
```bash
    select_backends
    select_agents
    if [ "$(uname -s)" != "Darwin" ]; then
        select_voxcode
    fi
    confirm_installation
```

VoxCode depends on local Whisper which has Linux-specific dependencies. Skip the step entirely on macOS rather than letting users hit errors.
