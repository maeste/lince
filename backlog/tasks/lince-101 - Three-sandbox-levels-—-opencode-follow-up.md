---
id: LINCE-101
title: Three sandbox levels — opencode follow-up
status: To Do
assignee: []
created_date: '2026-05-04 20:33'
updated_date: '2026-05-05 13:42'
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

## Lessons from lince-98 (don't repeat the bugs we already hit)

The claude prototype landed via PR #57. opencode is the trickiest of the four follow-ups because the **Bun/Landlock workaround interacts non-trivially with the paranoid bash wrapper**.

### Required for opencode (per-agent work)

1. **API key auto-mapping is provider-dependent.** opencode is a router, not a single-provider client — it forwards to whichever LLM the user has configured. Auto-map the most common ones in `sandbox/profiles/opencode-paranoid.toml`'s `[env.extra]`:
   ```toml
   [env.extra]
   OPENCODE_API_KEY = "$OPENCODE_API_KEY"
   ANTHROPIC_API_KEY = "$ANTHROPIC_API_KEY"
   OPENAI_API_KEY = "$OPENAI_API_KEY"
   GEMINI_API_KEY = "$GEMINI_API_KEY"
   ```
   `_collect_proxy_rules` skips empties and dedups by domain. Unset vars are silently dropped, so over-mapping is safe — the user gets exactly the providers they actually have configured.

2. **The Bun/Landlock workaround inside the paranoid bash wrapper is the hard bit.** opencode's existing `[agents.opencode-nono]` command (current agents-defaults.toml ~line 188) is:
   ```
   bash -c 'exec "$(dirname "$(readlink -f "$(which opencode)")")/.opencode" "$@"' --
   ```
   This bypasses the Node.js launcher's `spawnSync` (which crashes under Landlock with SIGABRT on Bun-based binaries). For paranoid+nono, the OUTER paranoid wrapper from `synthesize_sandboxed_command` is *also* a bash invocation that does scratch-copy + HOME override + nono run. The two must compose. Two safe forms:
   - **(a) Pass the bun-resolution as `inner_command`** — the outer paranoid wrapper joins this with shell_quote, embedding the inner bash as `'bash' '-c' '<resolution-script>' '--'` after `nono run ... --`. nono treats everything after `--` as argv and exec's it without further shell interpretation. Should work; **verify that `which opencode` resolves correctly inside the nono filesystem allowlist** — opencode's binary path needs to be readable through the profile's filesystem.read.
   - **(b) Pre-resolve the binary path on the host** before constructing the inner_command, embed the absolute path directly. Simpler runtime; loses a layer of indirection. Drawback: stale path if the user's `which opencode` changes between dashboard launches. Acceptable trade.
   Pick (a) or (b) and document in the doc page that opencode paranoid+bwrap is NOT needed for the same reason (bwrap doesn't use Landlock; the Bun/spawnSync bug doesn't apply). For paranoid+bwrap, the inner_command is just `["opencode"]`.

3. **Add an opencode match arm in `synthesize_sandboxed_command`**:
   - `agent_home_subdir`: `.config/opencode` — note this is **not flat under `$HOME`** like `.claude` / `.codex`. The rsync source/dest paths are `"$HOME/.config/opencode/"` and `"$SCRATCH/.config/opencode/"`. The current AGENT_HOME_SUBDIR placeholder is dropped into both — it's a relative path so subdirs work, but verify the bash form once.
   - `inner_command`: see (2) above.

4. **Permissive must passthrough `GH_TOKEN` / `GITHUB_TOKEN`** — copy from `claude-permissive.toml`.

5. **Do NOT enumerate `allow_domains` for known LLM providers** in paranoid. The credential rules already cover them. Ship `allow_domains = []` with the header pattern.

### Things ALREADY in master code (don't redo them)

- Fragment lookup with agent prefix.
- bwrap `--unshare-net` + outer unshare wrapper + socat + UID remap.
- Stale socket cleanup, proxy framing, BrokenPipe handling, fail-fast socat.
- shell_quote in the bash wrapper.

### Sanity checks before declaring done

```bash
agent-sandbox run -a opencode --sandbox-level paranoid -- bash

# 1. opencode binary launches inside paranoid (NO SIGABRT)
opencode --version || echo "BUG: Bun/Landlock workaround broken"

# 2. Scratch copy of ~/.config/opencode
ls -la ~/.config/opencode/

# 3. Kernel-level network block
curl -s https://attacker.com 2>&1   # netns-level fail

# 4. Whichever LLM provider the user has configured works through the proxy
# (depends on OPENCODE_API_KEY / ANTHROPIC_API_KEY / etc. on the host)
```

### Reference: lince-98 commits worth reading

- `077b37d3` (fragment lookup), `9b214451` (auto-map API key), `9142c367` (UID remap), `a7933b48` (unshare wrapper), `9e62cf12` (proxy framing), `858fe521` (GH_TOKEN passthrough), `405c3a11`/`5f987859` (review fixes).

For the Bun/Landlock workaround specifically, the existing `[agents.opencode-nono]` entry in `agents-defaults.toml` is the canonical reference.
<!-- SECTION:NOTES:END -->
