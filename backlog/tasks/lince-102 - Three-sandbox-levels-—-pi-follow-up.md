---
id: LINCE-102
title: Three sandbox levels — pi follow-up
status: To Do
assignee: []
created_date: '2026-05-04 20:33'
updated_date: '2026-05-05 18:11'
labels:
  - sandbox
  - lince-dashboard
  - follow-up
milestone: m-13
dependencies:
  - LINCE-98
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/52'
  - 'https://github.com/RisorseArtificiali/lince/issues/47'
  - 'https://github.com/RisorseArtificiali/lince/issues/48'
  - lince-dashboard/agents-defaults.toml
  - lince-dashboard/nono-profiles/lince-pi.json
documentation:
  - 'https://nono.sh/docs/cli/features/networking.md'
  - 'https://nono.sh/docs/cli/features/credential-injection.md'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Scope

Apply the three-level sandbox model to **pi**, following the pattern established in lince-98 (GH [#48](https://github.com/RisorseArtificiali/lince/issues/48)).

Tracks GH issue [#52](https://github.com/RisorseArtificiali/lince/issues/52). Umbrella: [#47](https://github.com/RisorseArtificiali/lince/issues/47).

> **Do not start until lince-98 is done.** Reuse the runtime dispatch logic and sandbox-policy mechanism.

## Background — full design context (no need to re-brainstorm)

LINCE today exposes `[agents.pi]` (unsandboxed), `[agents.pi-bwrap]`, `[agents.pi-nono]`. Collapse to a **single** `[agents.pi]` with `sandbox_level` + `sandbox_backend`.

## ⚠️ Pi-specific multi-provider complexity (CRITICAL)

Pi supports **18+ LLM providers** simultaneously. Current entries pass through env vars for: anthropic, openai, azure-openai, gemini (api+vertex), deepseek, mistral, groq, cerebras, cloudflare, xai, openrouter, ai-gateway, zai, opencode, fireworks, kimi, minimax (regular + cn), AWS Bedrock. See `agents-defaults.toml:214-246` for the full list.

This means **paranoid mode for pi cannot statically allowlist a single LLM endpoint** — the user has to declare which providers they actually use. Recommended approach:

- **paranoid**: introduce a config field `pi_providers = ["anthropic", "openai"]` that the plugin reads and translates to `network.credentials: [...]` for nono. Default: empty → no network at all (true paranoid). User must opt-in to specific providers.
- **normal**: today's behavior (env var passthrough)
- **permissive**: env var passthrough + github allowlist

This is the most architecturally interesting follow-up. Document the design decision clearly.

## Three levels — pi specifics

| | paranoid | normal | permissive |
|---|---|---|---|
| nono `network` | `credentials: $pi_providers` (user-declared subset) — empty means full block | inherited (`lince-pi.json`) | + github allowlist + credentials = full env passthrough |
| nono `filesystem` | `$WORKDIR` rw + scratch copy of `~/.pi` | as today | + standard permissive paths |
| bwrap | `use_real_config` equivalent forced (verify pi equivalent — `home_ro_dirs = ["~/.pi/"]`) + no-network | as today | + standard permissive paths |
| env vars | only declared providers' keys passed (rest filtered) | full passthrough | full passthrough |

## File touch list

**New:**
- `lince-dashboard/nono-profiles/lince-pi-paranoid.json`
- `lince-dashboard/nono-profiles/lince-pi-permissive.json`
- `sandbox/profiles/pi-paranoid.toml`
- `sandbox/profiles/pi-permissive.toml`

**Modified:**
- `lince-dashboard/agents-defaults.toml` — collapse pi entries (~lines 202-292 + 294-340), add `pi_providers` config field commentary
- `lince-dashboard/install.sh` — copy new nono profiles
- Plugin Rust: read `pi_providers` and translate to nono `credentials` array + filter env_vars accordingly

## References

- Multi-provider rationale: PR #40 ("agents/pi: passthrough all 18 Pi-supported provider env vars")
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agents-defaults.toml has a single [agents.pi] with sandbox_level/sandbox_backend + pi_providers field; pi-nono removed
- [ ] #2 pi_providers field respected: declared providers' keys passed in env; others filtered
- [ ] #3 paranoid with no pi_providers declared = full network block; pi can launch but cannot reach any LLM
- [ ] #4 paranoid with pi_providers=['anthropic'] = anthropic API works, others fail (e.g. openai unreachable)
- [ ] #5 Env-var filtering verified: 'printenv | grep _API_KEY' inside paranoid sandbox shows only declared providers
- [ ] #6 N-picker shows 'Pi' once
- [ ] #7 Master doc page extended with pi-specific rows: pi_providers design rationale, env-var filtering behavior, worked examples for paranoid with different provider subsets
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Documentation contribution

Master doc page (created by lince-98) already covers the overall mechanism. This task **extends** it with **pi-specific rows/notes**:
- Add pi row to the level-comparison table
- **Document the multi-provider design**: `pi_providers` field, why pi cannot statically allowlist a single LLM endpoint, how the field maps to nono `network.credentials` and to env-var filtering
- Worked example: paranoid with `pi_providers = ["anthropic"]` vs. paranoid with `pi_providers = ["anthropic", "openrouter"]` vs. paranoid with empty list (full block)
- Custom profile examples: e.g. `lince-pi-bedrock-only.json` extending normal with AWS Bedrock allowlist

Do **not** re-explain the overall mechanism.

## Lessons from lince-98 (don't repeat the bugs we already hit)

The claude prototype landed via PR #57. pi is the most architecturally interesting of the four follow-ups because of its **18+ provider env vars** and the design question around `pi_providers` (already raised in this task's description).

### Required for pi (per-agent work)

1. **API key auto-mapping is the EASY part for pi.** Every provider in pi's env passthrough list (see `[agents.pi.env_vars]` ~line 214 of agents-defaults.toml) that matches a `CREDENTIAL_PROXY_RULES` entry will get a proxy rule automatically. Auto-map all of them in `sandbox/profiles/pi-paranoid.toml`:
   ```toml
   [env.extra]
   ANTHROPIC_API_KEY = "$ANTHROPIC_API_KEY"
   ANTHROPIC_AUTH_TOKEN = "$ANTHROPIC_AUTH_TOKEN"
   OPENAI_API_KEY = "$OPENAI_API_KEY"
   GEMINI_API_KEY = "$GEMINI_API_KEY"
   GOOGLE_API_KEY = "$GOOGLE_API_KEY"
   # ...remaining 13+ providers...
   ```
   `_collect_proxy_rules` (sandbox/agent-sandbox:890) skips empties and dedups by domain — so over-mapping is safe. The user only gets rules for providers they have actually exported in their host env.

2. **The HARD part is `pi_providers` — design before code.** Auto-mapping all 18 vars makes paranoid "reachable to whichever providers the user has". That's already strict (kernel netns + per-domain proxy allowlist) but it's not user-controllable: a user with all 18 keys in env reaches all 18 endpoints. The description proposes a `pi_providers` config field for explicit subsetting. Two layers to decide:
   - **(a) Whitelist at proxy level**: `pi_providers = ["anthropic"]` → proxy only inserts rules for the anthropic key, even if other keys are in env. Simplest. Implementation: pass `pi_providers` to `_collect_proxy_rules` and filter out non-matching env vars before the rule scan.
   - **(b) Whitelist at env-passthrough level**: pi_providers also restricts which env vars cross into the sandbox. The agent inside doesn't even SEE keys for non-listed providers. Stricter. Implementation: filter `agent_cfg.env_vars` and `[env.extra]` before they hit `cmd += ["--setenv", ...]` in build_bwrap_cmd.
   - **(c) Both**: defense in depth. Probably the right answer, but more code.
   Document the decision in the fragment header AND in the master doc page (sandbox-levels.md). This is the architectural call this task exists to make.

3. **Add a pi match arm in `synthesize_sandboxed_command`**:
   - `agent_home_subdir`: `.pi`
   - `inner_command`: `vec!["pi".to_string()]`
   No internal-sandbox conflict (`bwrap_conflict = false`), no Bun workaround, no OAuth — pi is the simplest of the four for the bash-wrapper layer.

4. **Permissive must passthrough `GH_TOKEN` / `GITHUB_TOKEN`** — copy from `claude-permissive.toml`.

5. **Do NOT enumerate `allow_domains = ["api.anthropic.com", "api.openai.com", ...]`** in paranoid. The credential rules auto-include the matched domains. Ship `allow_domains = []` with the header pattern.

### Things ALREADY in master code (don't redo them)

- Fragment lookup with agent prefix.
- bwrap `--unshare-net` + outer unshare wrapper + socat bridge + UID remap.
- Stale socket cleanup, proxy framing fixes, BrokenPipe handling, fail-fast socat.
- shell_quote in the bash wrapper.

### Sanity checks before declaring done

```bash
agent-sandbox run -a pi --sandbox-level paranoid -- bash

# 1. Scratch copy of ~/.pi
ls -la ~/.pi/

# 2. Kernel network block
curl -s https://attacker.com 2>&1   # netns-level fail

# 3. Only allowlisted providers reachable
# With pi_providers = ["anthropic"], OPENAI_API_KEY in env:
curl -s -x http://127.0.0.1:8118 https://api.openai.com/v1/models
# expected: 403 from the proxy (key wasn't injected because openai is not in pi_providers)
# AND the OPENAI_API_KEY env var should NOT be visible inside the sandbox if you went with option (b) or (c) above:
printenv OPENAI_API_KEY    # empty
```

### Reference: lince-98 commits worth reading

- `077b37d3` (fragment lookup), `9b214451` (auto-map API key), `9142c367` (UID remap), `a7933b48` (unshare wrapper), `9e62cf12` (proxy framing), `7f5898c4` (BrokenPipe), `858fe521` (GH_TOKEN passthrough), `405c3a11`/`5f987859` (review fixes).
For pi's multi-provider model specifically, see the original PR #40 commit history (when the 18-var passthrough was added) and the `[agents.pi.env_vars]` block in `lince-dashboard/agents-defaults.toml`.

## 2026-05-05 — helper available since LINCE-99: `scratch_home_dirs`

LINCE-99 introduced a generic, agent-agnostic ephemeral scratch mechanism in `sandbox/agent-sandbox`. Use it instead of hand-rolling per-agent scratch logic on the bwrap path.

**What it does.** `agent_cfg.scratch_home_dirs` (list[str], default `[]`). When non-empty, `cmd_run` (bwrap path) creates a `tempfile.mkdtemp` per entry under `$XDG_RUNTIME_DIR` (or `/tmp`), `rsync -a`-seeds it from the real `~/<subdir>` if it exists, bind-mounts it over `$HOME/<subdir>` inside bwrap, and `shutil.rmtree`s it in the run's `finally` block. `build_bwrap_cmd` filters those subdirs out of `home_ro_dirs`/`home_rw_dirs` so the real dir is never bound — even briefly. Requires `rsync` on the host; agent-sandbox errors out with a clear install hint if it's missing.

**For pi.** Add to `sandbox/profiles/pi-paranoid.toml`:
```toml
[agents.pi]
scratch_home_dirs = [".pi"]
```
No other code change needed for the bwrap-paranoid scratch — agent-sandbox handles rsync, bind, and cleanup.

**Note on `pi_providers` filtering.** The `scratch_home_dirs` mechanism is purely about filesystem isolation of `~/.pi`. It does NOT affect env-var passthrough or proxy rule selection — those are still the architectural call this task has to make (option a/b/c in §2 of the existing notes). The two are orthogonal: scratch the config dir AND filter the env vars.

**For the nono path** (synthesized by `lince-dashboard/plugin/src/agent.rs::synthesize_sandboxed_command`), the existing bash-wrapper logic stays — add the pi match arm with `agent_home_subdir = ".pi"`. Both backends now give the same user-facing guarantee: ephemeral, per-run, fresh snapshot of `~/.pi`, discarded on exit.

**Reference.** See `sandbox/profiles/codex-paranoid.toml` (commit c60cadfc on `feature/lince-99-sandbox-levels-codex`) for the working pattern.
<!-- SECTION:NOTES:END -->
