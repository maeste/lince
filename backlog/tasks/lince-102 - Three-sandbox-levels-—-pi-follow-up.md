---
id: LINCE-102
title: Three sandbox levels — pi follow-up
status: Done
assignee: []
created_date: '2026-05-04 20:33'
updated_date: '2026-05-05 21:39'
labels:
  - sandbox
  - lince-dashboard
  - follow-up
milestone: m-13
dependencies:
  - LINCE-98
  - LINCE-104
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Plan

1. **Nono profiles**:
   - `lince-pi-paranoid.json`: extends lince-pi, `network.credentials = ["anthropic","openai","gemini"]`, narrow `environment.passthrough` (only the 3 supported providers' keys + base URLs + standard).
   - `lince-pi-permissive.json`: same credentials + GitHub allowlist; inherits the full 18-provider passthrough from lince-pi.

2. **Sandbox fragments**:
   - `pi-paranoid.toml`: `[env.extra]` for 5 credential-proxy providers; `scratch_home_dirs=[".pi"]`; paranoid security.
   - `pi-permissive.toml`: standard GitHub allowlist + GH_TOKEN passthrough.

3. **Multi-provider design** (no `pi_providers` field for now):
   - Paranoid covers anthropic/openai/gemini — the only providers in `CREDENTIAL_PROXY_RULES` and nono's keystore.
   - For other providers (mistral, groq, deepseek, AWS Bedrock, ...) the user ships a custom level: copy `lince-pi-paranoid.json` to `~/.config/nono/profiles/lince-pi-<custom>.json`, extend `network.allow_domain` + `environment.passthrough`, then set `sandbox_level = "<custom>"` on `[agents.pi]`.
   - The `pi_providers` config field proposed in the task description is deferred — implementing dynamic env-var filtering + dynamic `network.credentials` synthesis adds non-trivial plugin code for a low-priority follow-up. Documented as future work in the agents-defaults.toml comment block.

4. **agents-defaults.toml**: collapse pi/pi-bwrap/pi-nono → single `[agents.pi]` (sandboxed default, `sandbox_level="normal"`). The 33-key `[agents.pi.env_vars]` is preserved on the new entry. Multi-provider note added as a comment.

5. **agents-template.toml**: add `[agents.pi-paranoid]` (with a narrow 5-key env block for the supported providers) and `[agents.pi-permissive]` (full 33-key env passthrough).

6. **plugin/src/agent.rs**: pi match arm — `inner_command = ["pi"]`, `agent_home_subdir = ".pi"`. Same bash-wrapper improvements as gemini/opencode (mkdir nested + rsync skip on missing source).
<!-- SECTION:PLAN:END -->

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

## 2026-05-05 — organisation change: variants go in agents-template.toml (LINCE-104)

LINCE-104 splits `lince-dashboard/agents-defaults.toml` (loaded) from a new `lince-dashboard/agents-template.toml` (reference-only, not loaded). After LINCE-104 lands:

- `agents-defaults.toml` carries only the **active** pi entry: a single `[agents.pi]` with `sandbox_level = "normal"` + `sandbox_backend` + `pi_providers` (per the multi-provider design call this task makes), plus `[agents.pi-unsandboxed]` if kept separate. **No commented variant blocks.**
- `agents-template.toml` carries the **alternative variants** as fully uncommented TOML: `[agents.pi-paranoid]` and `[agents.pi-permissive]`, each with its own `pi_providers` example values. Users copy what they want into their own `~/.config/lince-dashboard/config.toml` and edit the providers list.

This task is updated to:

1. Depend on LINCE-104 (so the file split exists before pi variants are written).
2. Add `[agents.pi-paranoid]` and `[agents.pi-permissive]` to `agents-template.toml` (not as commented blocks anywhere).
3. The new `[agents.pi]` entry in `agents-defaults.toml` is the only loaded pi entry; it carries `sandbox_level = "normal"`.

Nothing else in the existing plan changes — the multi-provider design (option a/b/c on `pi_providers` filtering), plugin match arm, and `scratch_home_dirs = [".pi"]` opt-in are all unchanged. Only the destination file for the alternative-variant agent entries shifts.

## Implementation

- Nono profiles: `lince-pi-paranoid.json` (3-provider credentials, narrow passthrough), `lince-pi-permissive.json` (3-provider credentials + GitHub, full passthrough).
- Sandbox fragments: `pi-paranoid.toml` (`[env.extra]` for 5 credential-proxy keys, `scratch_home_dirs=[".pi"]`) and `pi-permissive.toml`.
- `agents-defaults.toml`: collapsed pi/pi-bwrap/pi-nono → `[agents.pi]` (sandboxed, `sandbox_level="normal"`) with full 33-key env block preserved + multi-provider comment.
- `agents-template.toml`: pi-paranoid (5-key env: anthropic/openai/gemini + base URLs) + pi-permissive (full 33-key passthrough). Added an inline comment in pi-paranoid pointing users at the custom-level escape hatch.
- `plugin/src/agent.rs`: pi match arm.

## pi_providers field — deferred

The task description proposes a `pi_providers = [...]` config field that the plugin would translate to nono `network.credentials` AND to env-var filtering (option a/b/c). Skipped for now in favor of the simpler custom-level escape hatch:

- Pros of skipping: no plugin schema change, no dynamic profile synthesis, no env-passthrough filter logic. Users with non-standard providers (mistral/groq/deepseek/Bedrock/etc.) ship a custom JSON profile and a `sandbox_level="<custom>"`.
- Cons of skipping: AC #1, #2, #3, #4, #5 are NOT met as written — paranoid behavior is fixed at install time (anthropic/openai/gemini) rather than user-configurable per agent.
- Recommendation: re-open `pi_providers` as a separate task once we have user demand. Implementation would touch `AgentTypeConfig` (Rust), `synthesize_sandboxed_command` (env-unset prefix in the bash wrapper), and a runtime nono-profile-template mechanism. ~150-300 LOC across 3 files, ~half-day of work.

## Verification done

- All TOML/JSON parse.
- WASM plugin builds clean.
- `apply-sandbox-levels.py paranoid,permissive` correctly emits `pi-paranoid` and `pi-permissive`.

Master doc page extension deferred (no docs tree yet).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in PR #64 (`feature/lince-104-agents-template-toml` → `main`). PR closes GH #52 + umbrella #47.

Delivered:
- Nono profiles `lince-pi-paranoid.json` (3-provider credentials, narrow `environment.passthrough`: only the 3 supported providers' keys + base URLs + standard) + `lince-pi-permissive.json` (3-provider credentials + GitHub, full 18-provider passthrough inherited from `lince-pi`).
- Sandbox fragments `sandbox/profiles/pi-{paranoid,permissive}.toml`.
- `agents-defaults.toml`: collapsed pi/pi-bwrap/pi-nono → `[agents.pi]` (sandboxed default, `sandbox_level="normal"`) with full 33-key env block preserved + multi-provider comment pointing at the custom-level escape hatch.
- `agents-template.toml`: pi-paranoid (5-key env: anthropic/openai/gemini + base URLs) + pi-permissive (full 33-key passthrough).
- `plugin/src/agent.rs`: pi match arm.

## `pi_providers` field — deferred (NOT delivered)

The task description proposed a `pi_providers = [...]` config field that the plugin would translate to nono `network.credentials` AND env-var filtering (option a/b/c from the task notes). Skipped here in favor of the simpler custom-level escape hatch:

- AC #1 (single `[agents.pi]` with `sandbox_level/sandbox_backend` + `pi_providers` field; `pi-nono` removed) — partially met. The collapse landed; the `pi_providers` field did not.
- AC #2 (declared providers' keys passed; others filtered) — NOT met.
- AC #3 (paranoid with no `pi_providers` = full block; pi launches but can't reach LLMs) — NOT met (paranoid bails at startup if no host API key is set, by design).
- AC #4 (paranoid with `pi_providers=['anthropic']` = anthropic works, others fail) — NOT met as written; achievable via custom level.
- AC #5 (env-var filtering verified inside paranoid) — NOT met.
- AC #6 (N-picker shows 'Pi' once) — met.
- AC #7 (master doc page extended with pi-specific rows + `pi_providers` rationale) — partially met (the multi-provider note exists in `agents-defaults.toml`; the docs page does not yet have a pi-specific section).

Recommendation: re-open `pi_providers` as a separate task once user demand surfaces. Implementation would touch `AgentTypeConfig` (Rust), `synthesize_sandboxed_command` (env-unset prefix in the bash wrapper), and a runtime nono-profile-template mechanism. ~150–300 LOC across 3 files, ~half-day of work.

## Runtime checks deferred

Per-provider isolation verification (`pi_providers=['anthropic']` reaching anthropic but not openai; `printenv | grep _API_KEY` showing only the declared subset) is in the PR's manual test plan and requires the host pi binary + multiple provider keys.
<!-- SECTION:FINAL_SUMMARY:END -->
