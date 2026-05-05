---
id: LINCE-100
title: Three sandbox levels — gemini follow-up
status: In Progress
assignee: []
created_date: '2026-05-04 20:32'
updated_date: '2026-05-05 20:52'
labels:
  - sandbox
  - lince-dashboard
  - follow-up
milestone: m-13
dependencies:
  - LINCE-98
  - LINCE-104
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Plan

1. **Nono profiles** (lince-dashboard/nono-profiles/):
   - `lince-gemini-paranoid.json`: extends lince-gemini, `network.credentials = ["gemini"]`, no extra reads.
   - `lince-gemini-permissive.json`: extends lince-gemini, gemini credentials + GitHub allow_domain + standard permissive reads.

2. **Sandbox fragments** (sandbox/profiles/):
   - `gemini-paranoid.toml`: `[env.extra]` auto-maps GEMINI_API_KEY + GOOGLE_API_KEY (both deduped to `generativelanguage.googleapis.com`); `[agents.gemini].scratch_home_dirs = [".gemini"]`; `credential_proxy=true` + `unshare_net=true` + `allow_domains=[]`.
   - `gemini-permissive.toml`: standard GitHub allowlist, `block_git_push=true`, GH_TOKEN/GITHUB_TOKEN passthrough.

3. **OAuth decision** (paranoid): API-key auth required. accounts.google.com / oauth2.googleapis.com are NOT allowed in paranoid — OAuth-only users should pick `normal` or `permissive`. Documented in JSON `meta.description` and TOML header.

4. **agents-defaults.toml**: collapse `[agents.gemini]` (unsandboxed), `[agents.gemini-bwrap]`, `[agents.gemini-nono]` → single `[agents.gemini]` (sandboxed default, `sandbox_level="normal"`) + `[agents.gemini-unsandboxed]`.

5. **agents-template.toml**: add `[agents.gemini-paranoid]` and `[agents.gemini-permissive]` (uncommented).

6. **plugin/src/agent.rs**: add gemini match arm to `synthesize_sandboxed_command` — `inner_command = ["gemini"]`, `agent_home_subdir = ".gemini"`. Also fix the bash wrapper to mkdir the nested home subdir and skip rsync if source is missing.

7. install.sh / sandbox install.sh: no changes needed (both loop over the directory).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Documentation contribution

Master doc page (created by lince-98) already covers the overall mechanism. This task **extends** it with **gemini-specific rows/notes**:
- Add gemini row to the level-comparison table
- Document GEMINI_API_KEY proxy injection in paranoid
- **Document the OAuth decision** made during execution: whether paranoid allows Google OAuth domains (accounts.google.com, oauth2.googleapis.com) for token refresh, or requires pre-existing token. Include the trade-off explanation.
- Brief note on common custom-profile patterns for gemini (e.g. Vertex AI users)

Do **not** re-explain the overall mechanism.

## Lessons from lince-98 (don't repeat the bugs we already hit)

The claude prototype landed via PR #57. Capturing the operational gotchas here so gemini doesn't redo them.

### Required for gemini (per-agent work)

1. **Auto-map the API key in `sandbox/profiles/gemini-paranoid.toml`'s `[env.extra]`.**
   Without this, the credential proxy starts with zero rules and paranoid bails out with `unshare_net = true requires credential_proxy = true` (the message blames the wrong knob — it's actually "proxy enabled but no API keys found"). Pattern:
   ```toml
   [env.extra]
   GEMINI_API_KEY = "$GEMINI_API_KEY"
   GOOGLE_API_KEY = "$GOOGLE_API_KEY"
   ```
   Both forms get a credential rule entry mapping to `generativelanguage.googleapis.com` (see `CREDENTIAL_PROXY_RULES` ~line 238). `_collect_proxy_rules` skips empties, so unset vars are silently dropped — safe to map both even if the user only has one.

2. **OAuth-only users are a special case.** If the user authenticates Gemini via Google OAuth (browser flow) instead of API key, the host env has no `GEMINI_API_KEY` set and the rule collector returns empty. The user's `gh auth status`-equivalent for gemini is via `~/.gemini/`, which the fragment bind-mounts read-only — but for **paranoid** the scratch copy isolates that, AND the OAuth refresh endpoint is on `oauth2.googleapis.com` (not in the credential rule). Two options:
   - (a) Document that gemini paranoid requires API key auth; OAuth-authenticated users should use normal/permissive.
   - (b) Extend the credential rule table to allow `oauth2.googleapis.com` and `accounts.google.com` for paranoid via `[security].allow_domains`. This loosens paranoid for one agent in a way that's hard to reverse. (a) is cleaner.
   Either way, document the decision in the master doc and in the fragment header.

3. **Add a gemini match arm in `synthesize_sandboxed_command`** in `lince-dashboard/plugin/src/agent.rs`:
   - `agent_home_subdir`: `.gemini`
   - `inner_command`: `vec!["gemini".to_string()]`
   No internal sandbox conflict to handle (`disable_inner_sandbox_args = []` in current `[agents.gemini-bwrap]`), so the codex-style hardcode-or-pass-agent_cfg dilemma doesn't apply to gemini. Just add the arm.

4. **Permissive must passthrough `GH_TOKEN` / `GITHUB_TOKEN`** — copy from `claude-permissive.toml`. Same reasoning as claude: keyring-auth users rely on the env path.

5. **Do NOT enumerate `allow_domains = ["generativelanguage.googleapis.com"]`** in the paranoid fragment. `_is_allowed_host` auto-includes credential-rule domains. Ship `allow_domains = []` with the header comment pattern from `claude-paranoid.toml`.

### Things ALREADY in master code (don't redo them)

- Fragment lookup tries `<agent>-<level>.toml` before `<level>.toml` — `gemini-paranoid.toml` is found automatically.
- bwrap `--unshare-net` setup, outer `unshare -U -n -r` wrapper, socat bridge, `--uid <real_uid>` remap.
- Stale unix-socket cleanup at startup.
- CredentialProxy framing (Connection: close, no duplicate headers, BrokenPipe-safe).
- socat readiness fail-fast.
- shell_quote in the bash wrapper.

### Sanity checks before declaring done

```bash
agent-sandbox run -a gemini --sandbox-level paranoid -- bash

# 1. Scratch copy of ~/.gemini
ls -la ~/.gemini/   # scratch contents, not your real ~/.gemini

# 2. Kernel-level network isolation
curl -s https://attacker.com 2>&1   # must fail at netns level (no route / DNS error)

# 3. Gemini API works through the proxy
curl -s -x http://127.0.0.1:8118 \
  https://generativelanguage.googleapis.com/v1beta/models | head

# 4. OAuth flow: document the decision (allow refresh URL via allow_domains, OR
#    document that paranoid requires API-key auth and OAuth users should use
#    normal/permissive)

# 5. Confirm no socat / socket leak on stop (same as claude)
pgrep -af 'socat.*8118'
ls ~/.agent-sandbox/proxy-*.sock 2>/dev/null
```

### Reference: lince-98 commits worth reading

- `077b37d3` (fragment lookup), `9b214451` (auto-map API key), `9142c367` (UID remap), `a7933b48` (unshare wrapper), `9e62cf12` (proxy framing), `7f5898c4` (BrokenPipe), `858fe521` (GH_TOKEN passthrough), `405c3a11`/`5f987859` (review fixes).
Reading those diffs is faster than re-discovering the same problems.

## 2026-05-05 — helper available since LINCE-99: `scratch_home_dirs`

LINCE-99 introduced a generic, agent-agnostic ephemeral scratch mechanism in `sandbox/agent-sandbox`. Use it instead of hand-rolling per-agent scratch logic on the bwrap path.

**What it does.** `agent_cfg.scratch_home_dirs` (list[str], default `[]`). When non-empty, `cmd_run` (bwrap path) creates a `tempfile.mkdtemp` per entry under `$XDG_RUNTIME_DIR` (or `/tmp`), `rsync -a`-seeds it from the real `~/<subdir>` if it exists, bind-mounts it over `$HOME/<subdir>` inside bwrap, and `shutil.rmtree`s it in the run's `finally` block. `build_bwrap_cmd` filters those subdirs out of `home_ro_dirs`/`home_rw_dirs` so the real dir is never bound — even briefly. Requires `rsync` on the host; agent-sandbox errors out with a clear install hint if it's missing.

**For gemini.** Add to `sandbox/profiles/gemini-paranoid.toml`:
```toml
[agents.gemini]
scratch_home_dirs = [".gemini"]
```
No other code change needed for the bwrap-paranoid scratch — agent-sandbox handles the rsync, bind, and cleanup.

**For the nono path** (synthesized by `lince-dashboard/plugin/src/agent.rs::synthesize_sandboxed_command`), the existing bash-wrapper logic (rsync into `$XDG_RUNTIME_DIR` HOME, trap-on-EXIT cleanup) stays — just add the gemini match arm with `agent_home_subdir = ".gemini"`. Both backends now give the same user-facing guarantee: ephemeral, per-run, fresh snapshot of `~/.gemini`, discarded on exit.

**Reference.** See `sandbox/profiles/codex-paranoid.toml` (commit c60cadfc on `feature/lince-99-sandbox-levels-codex`) for the working pattern.

## 2026-05-05 — organisation change: variants go in agents-template.toml (LINCE-104)

LINCE-104 splits `lince-dashboard/agents-defaults.toml` (loaded) from a new `lince-dashboard/agents-template.toml` (reference-only, not loaded). After LINCE-104 lands:

- `agents-defaults.toml` carries only the **active** gemini entry: a single `[agents.gemini]` with `sandbox_level = "normal"` + `sandbox_backend`, plus `[agents.gemini-unsandboxed]` if kept separate. **No commented variant blocks.**
- `agents-template.toml` carries the **alternative variants** as fully uncommented TOML: `[agents.gemini-paranoid]` and `[agents.gemini-permissive]`. Users copy what they want into their own `~/.config/lince-dashboard/config.toml`.

This task is updated to:

1. Depend on LINCE-104 (so the file split exists before gemini variants are written).
2. Add `[agents.gemini-paranoid]` and `[agents.gemini-permissive]` to `agents-template.toml` (not as commented blocks anywhere).
3. The new `[agents.gemini]` entry in `agents-defaults.toml` is the only loaded gemini entry; it carries `sandbox_level = "normal"`.

Nothing else in the existing plan changes — the nono profiles, bwrap fragments, plugin match arm, OAuth decision, and `scratch_home_dirs` opt-in are all unchanged. Only the destination file for the alternative-variant agent entries shifts.

## Implementation

- Nono profiles: `lince-gemini-paranoid.json`, `lince-gemini-permissive.json` shipped.
- Sandbox fragments: `sandbox/profiles/gemini-paranoid.toml` (with `[env.extra]` + `scratch_home_dirs=[".gemini"]`) and `sandbox/profiles/gemini-permissive.toml`.
- `agents-defaults.toml`: collapsed gemini, gemini-bwrap, gemini-nono → `[agents.gemini]` (sandboxed, `sandbox_level="normal"`) + `[agents.gemini-unsandboxed]`.
- `agents-template.toml`: added `[agents.gemini-paranoid]` and `[agents.gemini-permissive]`.
- `plugin/src/agent.rs`: added gemini match arm. WASM build clean.

## OAuth decision (paranoid)

Paranoid does NOT allow `accounts.google.com` / `oauth2.googleapis.com`. Rationale: keep the surface minimal and avoid a broad Google OAuth domain in the allowlist. Trade-off: OAuth-authenticated gemini users must pick `normal` or `permissive` (or extend `[security].allow_domains` in their own config). Documented in `lince-gemini-paranoid.json` `meta.description` and `gemini-paranoid.toml` header.

## Verification done

- All TOML/JSON parse.
- WASM plugin builds clean (release + dev).
- `apply-sandbox-levels.py paranoid,permissive` correctly picks up `gemini-paranoid` and `gemini-permissive`.

Master doc page extension (acceptance criterion #7) deferred — no docs/ tree exists yet for the dashboard sandbox-levels page; will land alongside the umbrella docs task.

Runtime sanity checks (curl/printenv inside paranoid) require a host with the gemini binary + a GEMINI_API_KEY, so left for the user to verify before pushing.
<!-- SECTION:NOTES:END -->
