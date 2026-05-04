---
id: LINCE-99
title: Three sandbox levels — codex follow-up
status: To Do
assignee: []
created_date: '2026-05-04 20:32'
updated_date: '2026-05-04 20:50'
labels:
  - sandbox
  - lince-dashboard
  - follow-up
milestone: m-13
dependencies:
  - LINCE-98
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/49'
  - 'https://github.com/RisorseArtificiali/lince/issues/47'
  - 'https://github.com/RisorseArtificiali/lince/issues/48'
  - lince-dashboard/agents-defaults.toml
  - lince-dashboard/nono-profiles/lince-codex.json
documentation:
  - 'https://nono.sh/docs/cli/features/networking.md'
  - 'https://nono.sh/docs/cli/features/credential-injection.md'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Scope

Apply the three-level sandbox model to **codex**, following the pattern established in lince-98 (GH [#48](https://github.com/RisorseArtificiali/lince/issues/48)).

Tracks GH issue [#49](https://github.com/RisorseArtificiali/lince/issues/49). Umbrella: [#47](https://github.com/RisorseArtificiali/lince/issues/47).

> **Do not start until lince-98 is done.** This task assumes the runtime dispatch logic in the lince-dashboard plugin and the sandbox-policy mechanism in `agent-sandbox` are already in place from the claude prototype. Reuse them; don't redesign.

## Background — full design context (no need to re-brainstorm)

LINCE today exposes `[agents.codex]` (unsandboxed), `[agents.codex-bwrap]`, `[agents.codex-nono]` as separate entries. Decision: collapse to a **single** `[agents.codex]` driven by:

- `sandbox_level = "paranoid" | "normal" | "permissive"` — default `"normal"`
- `sandbox_backend = "bwrap" | "nono"` — default per OS

`codex` (unsandboxed) becomes redundant if `sandbox_level = "off"` is supported by lince-98; otherwise keep as separate entry.

LLM provider for proxy/credential injection: **openai** (nono keystore account: `openai_api_key`).

## Codex-specific quirks (read carefully)

- `bwrap_conflict = true` on `codex-bwrap` — codex has its own internal sandbox that conflicts with bwrap. The current entry passes `disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]` to disable it. **Preserve this in all three levels.**
- `ignore_wrapper_start = true` — keep
- env var: `OPENAI_API_KEY` (passthrough today; in paranoid → injected by proxy, **not passed in env** to avoid leak)

## Three levels — codex specifics

| | paranoid | normal | permissive |
|---|---|---|---|
| nono `network` | `credentials: ["openai"]` | inherited from default preset | + `allow_domain` (api.github.com, github.com, objects.githubusercontent.com) + `credentials: ["openai"]` |
| nono `filesystem` | `$WORKDIR` rw + scratch copy of `~/.codex` | as today (`lince-codex.json`) | + `~/.config/gh`, `~/.cache`, `~/.ssh/known_hosts` (read) |
| bwrap | `use_real_config = false` forced + no-network + `disable_inner_sandbox_args` preserved | as today | + standard permissive paths + `disable_inner_sandbox_args` preserved |
| Tools | — | — | `gh` CLI (no docker, no podman, no direct `git push`) |

## File touch list

**New:**
- `lince-dashboard/nono-profiles/lince-codex-paranoid.json`
- `lince-dashboard/nono-profiles/lince-codex-permissive.json`
- `sandbox/profiles/codex-paranoid.toml`
- `sandbox/profiles/codex-permissive.toml`

**Modified:**
- `lince-dashboard/agents-defaults.toml` — collapse codex entries (~lines 38-70 + 147-164)
- `lince-dashboard/install.sh` — copy new nono profiles

## Out of scope

- docker/podman in permissive
- direct `git push` (use gh)
- Other agents (separate tasks)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agents-defaults.toml has a single [agents.codex] with sandbox_level/sandbox_backend; codex-nono removed
- [ ] #2 Codex internal sandbox conflict preserved across all three levels (no regression in disable_inner_sandbox_args = ['--sandbox', 'danger-full-access'])
- [ ] #3 OPENAI_API_KEY: passthrough in normal/permissive, proxy-injected in paranoid (no env var leak)
- [ ] #4 sandbox_level=paranoid on nono: only api.openai.com reachable; arbitrary outbound fails
- [ ] #5 sandbox_level=permissive: gh auth + gh pr work; docker ps fails
- [ ] #6 N-picker shows 'OpenAI Codex' once
- [ ] #7 Master doc page (sandbox-levels.md) extended with codex-specific rows: per-level behavior, codex quirks (inner-sandbox conflict, bwrap_conflict), OPENAI_API_KEY handling per level
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Documentation contribution

Master doc page (created by lince-98 at `docs/documentation/dashboard/sandbox-levels.md`) already explains:
- What paranoid/normal/permissive do in general
- The customization mechanism (`sandbox_level` as free-form profile suffix)
- The general worked example

This task **extends** that doc with **codex-specific rows/notes**:
- Add codex column or row to the level-comparison table (network, filesystem, tools per level)
- Document codex-specific quirks: inner-sandbox conflict (`disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]`), `bwrap_conflict = true`, OPENAI_API_KEY proxy injection in paranoid
- Brief note on which custom-profile patterns are common for codex (e.g. "lince-codex-with-azure" for Azure OpenAI users)

Do **not** re-explain the overall mechanism — link back to the master doc page.
<!-- SECTION:NOTES:END -->
