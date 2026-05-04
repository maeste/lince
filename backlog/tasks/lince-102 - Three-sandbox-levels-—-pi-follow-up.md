---
id: LINCE-102
title: Three sandbox levels — pi follow-up
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
<!-- SECTION:NOTES:END -->
