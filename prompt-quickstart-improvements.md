# Quickstart.sh — fix rustc → rustup prerequisite check

## Context

The `quickstart.sh` prerequisite checker validates `rustc` but the dashboard build requires WASM compilation (`wasm32-unknown-unknown` target). Distro-packaged `rustc` (via dnf/apt) does NOT ship the wasm32 standard library and there is no way to add it without `rustup`. Checking `rustc` gives a false positive on systems with distro Rust — the build fails later with a confusing `can't find crate for 'std'` error.

Additionally, when a user follows the install suggestion (`curl ... https://sh.rustup.rs | sh`) on a system that already has distro `rustc` at `/usr/bin/rustc`, the rustup installer blocks with `error: cannot install while Rust is installed`. The env var `RUSTUP_INIT_SKIP_PATH_CHECK=yes` skips only this PATH conflict check — all other prompts remain intact. Important: the env var must be on the `sh` side of the pipe, not the `curl` side.

## Change to make in `quickstart.sh`

### check_prerequisites function (around line 590)

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

That's it — single location, no other changes needed.
