---
id: LINCE-101
title: Three sandbox levels — opencode follow-up
status: To Do
assignee: []
created_date: '2026-05-04 20:33'
updated_date: '2026-05-04 20:50'
labels:
  - sandbox
  - lince-dashboard
  - follow-up
milestone: m-13
dependencies:
  - LINCE-98
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/51'
  - 'https://github.com/RisorseArtificiali/lince/issues/47'
  - 'https://github.com/RisorseArtificiali/lince/issues/48'
  - lince-dashboard/agents-defaults.toml
  - lince-dashboard/nono-profiles/lince-opencode.json
documentation:
  - 'https://nono.sh/docs/cli/features/networking.md'
  - 'https://nono.sh/docs/cli/features/credential-injection.md'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Scope

Apply the three-level sandbox model to **opencode**, following the pattern established in lince-98 (GH [#48](https://github.com/RisorseArtificiali/lince/issues/48)).

Tracks GH issue [#51](https://github.com/RisorseArtificiali/lince/issues/51). Umbrella: [#47](https://github.com/RisorseArtificiali/lince/issues/47).

> **Do not start until lince-98 is done.** Reuse the runtime dispatch logic and sandbox-policy mechanism.

## Background — full design context (no need to re-brainstorm)

LINCE today exposes `[agents.opencode]` (unsandboxed), `[agents.opencode-bwrap]`, `[agents.opencode-nono]` as separate entries. Collapse to a **single** `[agents.opencode]` with `sandbox_level` + `sandbox_backend`.

## ⚠️ OpenCode-specific Bun/Landlock workaround (CRITICAL)

OpenCode is Bun-based. **Bun-based binaries crash (SIGABRT) when spawned as subprocesses under Landlock.** Current workaround in `agents-defaults.toml:185-188`:

```toml
command = ["nono", "run", "--profile", "lince-opencode", "--workdir", "{project_dir}", "--",
           "bash", "-c", "exec \"$(dirname \"$(readlink -f \"$(which opencode)\")\")/.opencode\" \"$@\"", "--"]
```

This resolves the native binary and execs it directly, bypassing the Node.js launcher's `spawnSync`. **Preserve this command shape across all three nono levels.** For bwrap, verify whether the same issue applies (likely no, since bwrap doesn't use Landlock).

## LLM provider — open question (resolve during execution)

OpenCode uses `OPENCODE_API_KEY` (custom routing) and may not be tied to a single Anthropic/OpenAI/Gemini endpoint. **Verify during execution** what API endpoints opencode actually contacts at runtime (run with debug logging, or check opencode source/docs).

If opencode talks to many providers (like pi), paranoid mode needs one of:
- (a) Allow only the specific provider the user has configured (require user to declare it)
- (b) Allow `network.credentials: ["openai", "anthropic", "gemini"]` collectively
- (c) A permissive variant of paranoid that allows the user's set

Decide and document the trade-off.

## Three levels — opencode specifics

| | paranoid | normal | permissive |
|---|---|---|---|
| nono `network` | TBD (see provider question above) | inherited (`lince-opencode.json`) | + github allowlist |
| nono `filesystem` | `$WORKDIR` rw + scratch copy of `~/.config/opencode` | as today | + standard permissive paths |
| bwrap | `use_real_config = false` forced (verify opencode equivalent — `home_ro_dirs = ["~/.config/opencode/"]` today) + no-network | as today | + standard permissive paths |
| Bun workaround | preserve in command | preserve | preserve |
| Tools | — | — | `gh` CLI (no docker, no podman, no `git push`) |

## File touch list

**New:**
- `lince-dashboard/nono-profiles/lince-opencode-paranoid.json`
- `lince-dashboard/nono-profiles/lince-opencode-permissive.json`
- `sandbox/profiles/opencode-paranoid.toml`
- `sandbox/profiles/opencode-permissive.toml`

**Modified:**
- `lince-dashboard/agents-defaults.toml` — collapse opencode entries (~lines 104-128 + 184-200)
- `lince-dashboard/install.sh` — copy new nono profiles
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agents-defaults.toml has a single [agents.opencode] with sandbox_level/sandbox_backend; opencode-nono removed
- [ ] #2 Bun/Landlock workaround preserved in all three nono levels (no SIGABRT regression)
- [ ] #3 Documented decision on opencode's LLM endpoint allowlist for paranoid (which providers, why)
- [ ] #4 OPENCODE_API_KEY handling documented (likely passthrough; not a 'credentials' provider in nono)
- [ ] #5 N-picker shows 'OpenCode' once
- [ ] #6 sandbox_level=permissive: gh CLI works; docker ps fails
- [ ] #7 Master doc page extended with opencode-specific rows: Bun/Landlock workaround explained, LLM-endpoint allowlist decision documented, OPENCODE_API_KEY handling per level
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Documentation contribution

Master doc page (created by lince-98) already covers the overall mechanism. This task **extends** it with **opencode-specific rows/notes**:
- Add opencode row to the level-comparison table
- **Document the Bun/Landlock workaround** prominently — it's the most surprising opencode-specific behavior. Explain why the command is wrapped in `bash -c "exec ..."` and that this must be preserved across all levels.
- Document the LLM-endpoint allowlist decision made during execution (which providers are allowed in paranoid for opencode; rationale)
- Document OPENCODE_API_KEY handling per level (passthrough vs. proxy injection)

Do **not** re-explain the overall mechanism.
<!-- SECTION:NOTES:END -->
