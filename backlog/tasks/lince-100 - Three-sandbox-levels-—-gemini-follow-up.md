---
id: LINCE-100
title: Three sandbox levels — gemini follow-up
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
  - 'https://github.com/RisorseArtificiali/lince/issues/50'
  - 'https://github.com/RisorseArtificiali/lince/issues/47'
  - 'https://github.com/RisorseArtificiali/lince/issues/48'
  - lince-dashboard/agents-defaults.toml
  - lince-dashboard/nono-profiles/lince-gemini.json
documentation:
  - 'https://nono.sh/docs/cli/features/networking.md'
  - 'https://nono.sh/docs/cli/features/credential-injection.md'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Scope

Apply the three-level sandbox model to **gemini**, following the pattern established in lince-98 (GH [#48](https://github.com/RisorseArtificiali/lince/issues/48)).

Tracks GH issue [#50](https://github.com/RisorseArtificiali/lince/issues/50). Umbrella: [#47](https://github.com/RisorseArtificiali/lince/issues/47).

> **Do not start until lince-98 is done.** Reuse the runtime dispatch logic and sandbox-policy mechanism from the claude prototype.

## Background — full design context (no need to re-brainstorm)

LINCE today exposes `[agents.gemini]` (unsandboxed), `[agents.gemini-bwrap]`, `[agents.gemini-nono]` as separate entries. Collapse to a **single** `[agents.gemini]` with `sandbox_level` + `sandbox_backend`, alternative levels as commented templates.

LLM provider for proxy/credential injection: **gemini** (nono keystore account: `gemini_api_key`).

## Gemini-specific notes

- `disable_inner_sandbox_args = []` — no internal sandbox conflict
- env var: `GEMINI_API_KEY` (passthrough today; in paranoid → injected by proxy)
- **Verify during execution**: gemini CLI may require Google OAuth domains (accounts.google.com, oauth2.googleapis.com) if user is logged in via OAuth instead of API key. Check actual auth flow with debug logging or strace.

## Three levels — gemini specifics

| | paranoid | normal | permissive |
|---|---|---|---|
| nono `network` | `credentials: ["gemini"]` (verify if Google OAuth domains needed) | inherited | + `allow_domain` (github + objects) + `credentials: ["gemini"]` |
| nono `filesystem` | `$WORKDIR` rw + scratch copy of `~/.gemini` | as today (`lince-gemini.json`) | + `~/.config/gh`, `~/.cache`, `~/.ssh/known_hosts` (read) |
| bwrap | `use_real_config = false` forced + no-network | as today | + standard permissive paths |
| Tools | — | — | `gh` CLI (no docker, no podman, no `git push`) |

## File touch list

**New:**
- `lince-dashboard/nono-profiles/lince-gemini-paranoid.json`
- `lince-dashboard/nono-profiles/lince-gemini-permissive.json`
- `sandbox/profiles/gemini-paranoid.toml`
- `sandbox/profiles/gemini-permissive.toml`

**Modified:**
- `lince-dashboard/agents-defaults.toml` — collapse gemini entries (~lines 72-101 + 166-182)
- `lince-dashboard/install.sh` — copy new nono profiles

## Decision point during execution

If Gemini OAuth requires additional Google domains:
- Document them in profile comment
- Add to permissive `allow_domain`
- For paranoid: decide whether to allow OAuth refresh (more network) or require pre-existing token (more lockdown). Document the trade-off.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agents-defaults.toml has a single [agents.gemini] with sandbox_level/sandbox_backend; gemini-nono removed
- [ ] #2 GEMINI_API_KEY: passthrough in normal/permissive, proxy-injected in paranoid
- [ ] #3 sandbox_level=paranoid on nono: only Gemini API endpoints reachable; arbitrary outbound fails
- [ ] #4 sandbox_level=permissive: gh auth + gh pr work; docker ps fails
- [ ] #5 N-picker shows 'Google Gemini CLI' once
- [ ] #6 OAuth flow behavior documented for paranoid (allow refresh or require pre-existing token)
- [ ] #7 Master doc page extended with gemini-specific rows and OAuth trade-off explanation for paranoid (allow refresh vs. require pre-existing token)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Documentation contribution

Master doc page (created by lince-98) already covers the overall mechanism. This task **extends** it with **gemini-specific rows/notes**:
- Add gemini row to the level-comparison table
- Document GEMINI_API_KEY proxy injection in paranoid
- **Document the OAuth decision** made during execution: whether paranoid allows Google OAuth domains (accounts.google.com, oauth2.googleapis.com) for token refresh, or requires pre-existing token. Include the trade-off explanation.
- Brief note on common custom-profile patterns for gemini (e.g. Vertex AI users)

Do **not** re-explain the overall mechanism.
<!-- SECTION:NOTES:END -->
