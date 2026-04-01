# Quickstart.sh UX improvements — make the installer more self-explanatory

## Context

We've updated the lince.sh homepage to add a "Sandbox Backends" section that explains the configure-now-choose-at-runtime model. A real user tested the installer and had these confusions:

1. **Didn't understand why backends are multi-select** — thought it was a mutually exclusive choice of THE sandbox, not "configure which options will be available at runtime"
2. **Didn't understand what happens if both bwrap AND nono are selected** — which one is used?
3. **Thought "Unsandboxed" shouldn't need configuration** — if it's no sandbox, why configure it?
4. **Thought nono was macOS-only** — the description doesn't mention it works on Linux too (via Landlock)
5. **The one-line descriptions don't differentiate bwrap vs nono enough** — user can't make an informed choice

The goal is NOT to make the installer verbose — just add enough context that a user who has quickly read lince.sh can follow along without getting confused. A few extra lines of text in the right places.

## Changes to make in `quickstart.sh`

### 1. Step 1 intro text (select_backends function, around line 88)

Current:
```
echo -e "  LINCE wraps your AI agents in a sandbox so they can code"
echo -e "  freely without reaching your SSH keys, credentials, or"
echo -e "  pushing to production. Select which backends to configure."
```

Replace with something like:
```
echo -e "  LINCE can wrap each AI agent in a sandbox so it can code"
echo -e "  freely without reaching your SSH keys, credentials, or"
echo -e "  pushing to production."
echo -e ""
echo -e "  ${DIM}Select which backends to make available. Each time you${NC}"
echo -e "  ${DIM}launch an agent, you choose which backend to use.${NC}"
```

The key message is: **you're configuring what's available, not making a one-time choice.** The second line clarifies that the choice happens per-agent at launch time.

### 2. Backend descriptions (BACKENDS array, around line 49)

Current:
```bash
BACKENDS=(
    "bwrap|bubblewrap (bwrap)|Same technology as Flatpak. Battle-tested, zero overhead."
    "nono|nono|Landlock LSM (Linux) + Seatbelt (macOS). Newer, cross-platform."
    "unsandboxed|Unsandboxed|Agents run directly on your system — no isolation."
)
```

Replace with:
```bash
BACKENDS=(
    "bwrap|bubblewrap (bwrap)|Built-in sandbox. Same technology as Flatpak. Minimal, zero dependencies."
    "nono|nono (nono.sh)|External sandbox with network isolation. Landlock (Linux) + Seatbelt (macOS)."
    "unsandboxed|Unsandboxed|No isolation — agent runs with full host access."
)
```

Key differences:
- bwrap: emphasize "Built-in" and "zero dependencies" (it's LINCE's own, minimal by design)
- nono: say "External sandbox" (it's an integration with nono.sh), mention "network isolation" (its differentiator), clarify it works on BOTH Linux and macOS
- unsandboxed: "full host access" is clearer than "no isolation"

### 3. Fix "sudo dnf install bubblewrap" in backend selector (around line 118)

Current:
```bash
else status=" ${YELLOW}(not installed — sudo dnf install bubblewrap)${NC}"; fi
```

This is distro-specific. Replace with a more generic hint:
```bash
else status=" ${YELLOW}(not installed — see https://github.com/containers/bubblewrap#installation)${NC}"; fi
```

Or shorter:
```bash
else status=" ${YELLOW}(not installed)${NC}"; fi
```

Since the prerequisite checker later will give detailed install instructions anyway, keeping it short here avoids the dnf/apt bias. The `(not installed)` marker is enough for the user to know they need to install it.

### 4. Fix rustc check → rustup check (check_prerequisites function, around line 590)

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
    echo -e "      ${DIM}Install: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh${NC}"
fi
```

Why: distro-packaged `rustc` (via dnf/apt) cannot compile WASM because it doesn't ship the `wasm32-unknown-unknown` standard library. Only `rustup` can provide wasm targets via `rustup target add`. Checking `rustc` gives a false positive on systems with distro Rust but no rustup — the build will fail later with a confusing "can't find crate for std" error.

### 5. "bubblewrap not found" in check_prerequisites (around line 615)

Current:
```bash
echo -e "  ${YELLOW}✗${NC} bubblewrap — ${DIM}sudo dnf install bubblewrap${NC}"
```

Replace with:
```bash
echo -e "  ${YELLOW}✗${NC} bubblewrap — ${DIM}install via your package manager (dnf/apt/pacman)${NC}"
```

This avoids suggesting a single distro's package manager.

### Summary of changes

| Location | What | Why |
|----------|------|-----|
| Step 1 intro (~line 88) | Explain configure-now-choose-later model | User thought it was a one-time global choice |
| BACKENDS array (~line 49) | Better descriptions for bwrap/nono/unsandboxed | User couldn't differentiate or thought nono was macOS-only |
| Backend selector (~line 118) | Remove `sudo dnf install` hint | Distro-specific, and prereq checker handles it later |
| check_prerequisites (~line 590) | Check `rustup` instead of `rustc` | Distro rustc can't compile WASM |
| check_prerequisites (~line 615) | Generic package manager hint | Don't assume dnf |

### What NOT to change

- The unsandboxed warning box is excellent — keep it as-is
- The agent selection (Step 2) text is already clear
- The VoxCode section (Step 3) is already well-explained
- The installation summary is good — it already shows backends per agent
- Don't add links to docs in every step — the user has read lince.sh, keep it concise
