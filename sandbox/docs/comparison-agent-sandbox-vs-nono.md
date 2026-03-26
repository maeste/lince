# Comparison: agent-sandbox vs nono

**Date**: 2026-03-26
**Context**: Evaluating [always-further/nono](https://github.com/always-further/nono) against our bubblewrap-based agent-sandbox.

---

## Overview

| | **agent-sandbox** (lince) | **nono** (always-further) |
|---|---|---|
| **Author** | lince project | Luke Hinds (Sigstore founder) |
| **Language** | Python 3.11+, single file (~1,330 lines) | Rust, ~76+ source files (~15-25K lines) |
| **Isolation tech** | Bubblewrap (Linux namespaces) | Landlock LSM + Seatbelt (macOS) |
| **Kernel requirement** | 3.8+ | 5.13+ (full network: 6.6+) |
| **Platform** | Linux only | Linux + macOS |
| **Dependencies** | Zero (Python stdlib + bwrap binary) | Substantial (tokio, hyper, sigstore, aws-lc-rs...) |
| **Maturity** | Working, stable | Alpha (v0.24.0), ~30 releases in 6 weeks |
| **Stars** | Private/small | ~1,300 |

---

## Where nono is stronger

### 1. Finer-grained filesystem control
Landlock provides per-path read/write/readwrite rules at the kernel level. Our bwrap approach is mount-based — whole directories are either read-only or writable. nono can say "this specific file is writable, its sibling is not."

### 2. Credential isolation is architecturally superior
nono's proxy injects credentials into outbound requests — secrets never enter the sandbox process memory at all. Our sandbox strips git credentials and env vars (good), but API keys for the agent itself must still exist inside the sandbox.

### 3. Filesystem rollback
Content-addressable snapshots with SHA-256 dedup and Merkle tree verification. You can undo what the agent did atomically. agent-sandbox has no rollback — damage within the writable project dir sticks (we rely on git).

### 4. Supervised capability elevation
Via seccomp user notification, nono can intercept syscalls and prompt the user before allowing access to new paths at runtime. agent-sandbox is static — the sandbox shape is fixed at launch.

### 5. macOS support
Via Seatbelt (though it's deprecated by Apple, which is a risk).

### 6. Instruction file trust
Sigstore-based signing of CLAUDE.md/AGENTS.md prevents prompt injection via tampered instruction files.

### 7. Learn mode
Automatically discovers what capabilities an agent actually needs by tracing syscalls, then generates a profile.

---

## Where agent-sandbox is stronger

### 1. Zero dependencies, dead simple
One Python file, stdlib only, one system binary (bwrap). nono pulls in tokio, hyper, aws-lc-rs, sigstore — that's a large attack surface and compile time for a security tool. Our tool is auditable in an afternoon.

### 2. Mature multi-agent orchestration
Config-driven agent types with per-agent env vars, bwrap conflict handling (e.g., Codex uses bwrap internally — we handle the nesting), profile-based API key management, all in one config file. nono has per-agent profiles but no awareness of agent-specific quirks like inner sandbox conflicts.

### 3. Config diff/merge workflow
Isolated config copy → `agent-sandbox diff` → `agent-sandbox merge` — a thoughtful workflow for reviewing what the agent changed before applying to real `~/.claude/`. nono doesn't have this.

### 4. Build toolchain persistence
Careful split of writable caches vs read-only binaries for cargo, npm, go, uv. Auto-detection of `$PATH` toolchains. nono has basic workspace write access but no special handling of build tool caches across sessions.

### 5. Lince/Zellij integration
Re-exposes Zellij sockets, passes `LINCE_AGENT_ID`, integrates with the TUI dashboard. Domain-specific but valuable for our ecosystem.

### 6. Battle-tested simplicity
bwrap is the same tech that powers Flatpak — extensively audited, used by millions. Landlock is newer and less battle-tested at the application layer.

### 7. PID namespace isolation
Host processes are invisible to the agent. nono has signal scoping (Landlock V6, kernel 6.11+) but no full PID namespace — the agent can still see host PIDs.

### 8. Wider kernel compatibility
Works on kernel 3.8+. nono requires 5.13+ for basic functionality, 6.6+ for network filtering. Many enterprise/LTS distros don't ship 6.6 yet.

---

## Roughly equal areas

- **Git push blocking**: We use a 3-layer defense (wrapper + config sanitization + no credentials). nono blocks via destructive command deny list + credential proxy. Both effective, different approaches.
- **Network**: Both leave the network open by default (agents need API access). nono has proxy-based allowlisting which is more granular but also more complex. Neither does network namespace isolation.
- **Multi-agent profiles**: Both support Claude, Codex, OpenCode, and others via config/profiles.
- **Session logging**: We have transcript capture. nono has structured JSON audit trails. Different formats, similar goal.

---

## Assessment

**nono is more ambitious and architecturally sophisticated.** Landlock per-path control, credential proxy isolation, rollback snapshots, Sigstore trust, and supervised capability elevation are genuinely advanced features. Designed by someone with deep security credentials.

**agent-sandbox is more practical and production-ready today.** Zero dependencies, one auditable file, wider kernel support, thoughtful developer workflow (diff/merge), and battle-tested isolation tech (bwrap/namespaces). It solves the actual problem — "don't let the AI wreck my machine" — without over-engineering.

**Key philosophical difference:** nono aims to be a comprehensive security framework with defense-in-depth. agent-sandbox aims to be a pragmatic safety net that's easy to understand and trust. Both are valid approaches.

### Recommendation for third parties
- Modern Fedora/Arch workstation, wanting maximum security? Try nono, but know it's alpha.
- Any Linux, wanting something reliable today with zero friction? agent-sandbox.
- Long-term, nono's Landlock approach is arguably the better foundation — but it needs to mature, get audited, and shed the alpha label.

---

## Improvement opportunities for agent-sandbox (from nono)

1. **Credential proxy isolation** — keeping API keys out of the sandbox entirely
2. **Filesystem rollback** — even a simple rsync-based approach would add value
3. **Learn mode** — trace what the agent actually touches, tighten the sandbox

## What nono could learn from agent-sandbox

1. Config diff/merge workflow for isolated agent configs
2. Build toolchain cache management (read-only tools / writable caches split)
3. Inner sandbox conflict handling (bwrap-inside-bwrap for Codex)
4. The value of zero dependencies in a security tool
