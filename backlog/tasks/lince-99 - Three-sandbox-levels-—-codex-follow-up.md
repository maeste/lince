---
id: LINCE-99
title: Three sandbox levels — codex follow-up
status: In Progress
assignee:
  - claude
created_date: '2026-05-04 20:32'
updated_date: '2026-05-05 17:19'
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
- [x] #1 agents-defaults.toml has a single [agents.codex] with sandbox_level/sandbox_backend; codex-nono removed
- [x] #2 Codex internal sandbox conflict preserved across all three levels (no regression in disable_inner_sandbox_args = ['--sandbox', 'danger-full-access'])
- [x] #3 OPENAI_API_KEY: passthrough in normal/permissive, proxy-injected in paranoid (no env var leak)
- [ ] #4 sandbox_level=paranoid on nono: only api.openai.com reachable; arbitrary outbound fails
- [ ] #5 sandbox_level=permissive: gh auth + gh pr work; docker ps fails
- [x] #6 N-picker shows 'OpenAI Codex' once
- [x] #7 Master doc page (sandbox-levels.md) extended with codex-specific rows: per-level behavior, codex quirks (inner-sandbox conflict, bwrap_conflict), OPENAI_API_KEY handling per level
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation plan

Branch: `feature/lince-99-sandbox-levels-codex` (off main).

### 1. New files

**Nono profiles** (`lince-dashboard/nono-profiles/`):
- `lince-codex-paranoid.json` — extends `lince-codex`; `network.credentials = ["openai"]`; `filesystem.allow = ["$WORKDIR", "$HOME"]` (per-agent scratch HOME, real home not mounted; bash wrapper supplies the per-agent scratch); no `allow_domain` (auto-included from credential rule, mirroring claude-paranoid).
- `lince-codex-permissive.json` — extends `lince-codex`; `network.credentials = ["openai"]` + `allow_domain: [api.github.com, github.com, objects.githubusercontent.com]` + `network_profile: "developer"`; `filesystem.read` adds `$HOME/.config/gh`, `$HOME/.cache`, `$HOME/.ssh/known_hosts`.

**Bwrap fragments** (`sandbox/profiles/`):
- `codex-paranoid.toml` — `[env.extra] OPENAI_API_KEY = "$OPENAI_API_KEY"` (auto-rule); `[security] credential_proxy = true`, `unshare_net = true`, `allow_domains = []` (api.openai.com auto-included). NO `[claude]` block (codex has its own state in `~/.codex` — see "scratch limitation" below).
- `codex-permissive.toml` — `[sandbox] home_ro_dirs = [".config/gh", ".cache", ".ssh/known_hosts"]`; `[env] passthrough = ["GH_TOKEN", "GITHUB_TOKEN"]`; `[security] credential_proxy = true`, `block_git_push = true`, `allow_domains = ["api.github.com", "github.com", "objects.githubusercontent.com"]`.

### 2. Modified files

**`lince-dashboard/agents-defaults.toml`**:
- Rename `[agents.codex]` (current, unsandboxed) → `[agents.codex-unsandboxed]` to match claude pattern.
- Remove `[agents.codex-bwrap]` and `[agents.codex-nono]`.
- Add a single new `[agents.codex]` entry: `sandboxed = true`, `sandbox_level = "normal"`, `bwrap_conflict = true`, `disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]`, `home_ro_dirs = ["~/.codex/"]`, `ignore_wrapper_start = true`, `env_vars.OPENAI_API_KEY = "$OPENAI_API_KEY"`, color `cyan`. Mirror claude's commented `-paranoid` / `-permissive` example blocks.

**`lince-dashboard/plugin/src/agent.rs`** — `synthesize_sandboxed_command`:
- Add `"codex"` match arm: `inner_command = ["codex", "--full-auto", "--sandbox", "danger-full-access"]` (hardcode disable_inner_sandbox_args for nono path; bwrap path goes through agent-sandbox which reads `agent_cfg.disable_inner_sandbox_args` from sandbox/agents-defaults.toml as today).
- Add `agent_home_subdir = ".codex"` for paranoid bash wrapper.
- For **AgentSandbox** (bwrap) backend: always emit `--agent <base>` so codex (and future gemini/opencode/pi) lands in agent-sandbox's per-agent dispatch. Claude's case is unchanged in behavior because `--agent claude` matches the script default.

**`docs/documentation/dashboard/sandbox-levels.md`**:
- Append a "### 8. Per-agent specifics — codex" section: per-level table row(s), inner-sandbox conflict (`--sandbox danger-full-access`) note, OPENAI_API_KEY proxy injection, brief note on common custom levels (e.g. `lince-codex-with-azure` for Azure OpenAI).
- Brief footnote: under bwrap paranoid, real `~/.codex` is still bind-mounted RW (no codex-side `use_real_config` mechanism today); under nono paranoid, the bash wrapper rsyncs to a scratch HOME and discards on stop. nono is the strongest paranoid backend for codex.

### 3. install.sh
No change — `lince-dashboard/install.sh` already copies every `lince-*.json` and the bwrap fragment files are picked up by agent-sandbox from its profiles dir on a fresh install.

### 4. Manual verification (per AC)
1. `agent-sandbox run -a codex --sandbox-level paranoid --dry-run -p .` → bwrap argv contains `--unshare-user --uid <real_uid>`, no OPENAI_API_KEY, HTTP_PROXY set, codex receives `--sandbox danger-full-access`.
2. nono paranoid sandbox: `curl https://attacker.com` fails kernel-side, `curl -x http://127.0.0.1:8118 https://api.openai.com/v1/models` returns 200.
3. permissive: `gh auth status` works, `docker ps` fails (binary not present).
4. N-picker: only one entry labeled "OpenAI Codex" (the new `[agents.codex]`); `codex-unsandboxed` shows separately.

### 5. Out of scope (explicit)
- Bwrap-paranoid scratch `~/.codex` (would need a codex analog of `[claude] use_real_config = false`; not blocking ACs since #4 specifies nono for paranoid network isolation).
- docker / podman in permissive.
- direct `git push` (gh-only).
- gemini / opencode / pi (separate tasks).
<!-- SECTION:PLAN:END -->

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

## Lessons from lince-98 (don't repeat the bugs we already hit)

The claude prototype landed via PR #57 with 14+ commits, several of which were bug-fix iterations on issues that surfaced *during* execution. Capturing them here so codex doesn't redo them.

### Required for codex (per-agent work)

1. **Auto-map the API key in `sandbox/profiles/codex-paranoid.toml`'s `[env.extra]`.**
   Without this, the credential proxy starts with zero rules and paranoid bails out with `unshare_net = true requires credential_proxy = true` (which is misleading because the proxy IS enabled — it just has nothing to inject). Pattern:
   ```toml
   [env.extra]
   OPENAI_API_KEY = "$OPENAI_API_KEY"
   ```
   OpenAI does not have an `_AUTH_TOKEN` variant; one entry is enough. `_expand_env_value` returns empty string for unset host vars, and `_collect_proxy_rules` skips empties (sandbox/agent-sandbox:905), so this is safe even if the user hasn't exported the var — they just get the same "no rules" error which is the right outcome.

2. **Add a codex match arm in `synthesize_sandboxed_command`** in `lince-dashboard/plugin/src/agent.rs`:
   - `agent_home_subdir`: `.codex`
   - `inner_command`: `vec!["codex".to_string(), "--full-auto".to_string()]`
   You also need to handle the **codex inner-sandbox conflict** that breaks bwrap nesting. The existing `[agents.codex-bwrap]` entry passes `disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]`. The synthesized argv currently does NOT read these from `agent_cfg`, so either hardcode them into codex's `inner_command` arm, or extend `synthesize_sandboxed_command` to take `agent_cfg` and append `disable_inner_sandbox_args` like the legacy path does (build_bwrap_cmd ~line 1917). Pick one and stick to it for the gemini/opencode/pi tasks.

3. **Permissive must passthrough `GH_TOKEN` / `GITHUB_TOKEN`.** Copy the `[env]\npassthrough = ["GH_TOKEN", "GITHUB_TOKEN"]` block from `sandbox/profiles/claude-permissive.toml`. Users on gh keyring auth rely on the env-var path; the default `--clearenv` in bwrap wipes them otherwise.

4. **Do NOT enumerate `allow_domains = ["api.openai.com"]`** in the paranoid fragment. `_is_allowed_host` already auto-includes any domain that has a credential rule. Ship `allow_domains = []` with a header comment showing how users extend it — same shape as `claude-paranoid.toml`. This was a back-and-forth in the review and the empty-list version is the correct one.

### Things ALREADY in master code (don't redo them)

- Fragment lookup tries `<agent>-<level>.toml` before `<level>.toml` (commit 077b37d3) — your `codex-paranoid.toml` is found automatically.
- bwrap `--unshare-net` is set up by `cmd_run` via an outer `unshare -U -n -r` wrapper that brings up `lo`, runs socat as a TCP→unix-socket bridge, then exec's bwrap with `--unshare-user --uid <real_uid> --gid <real_gid>` so the agent does NOT inherit `getuid()==0` (Claude refused `--dangerously-skip-permissions` early on for that exact reason — same applies to codex's `--full-auto`).
- Stale `~/.agent-sandbox/proxy-PID.sock` files from killed runs are swept at startup.
- CredentialProxy framing fixes are global: `Connection: close`, no duplicate `Date`/`Server`, no stale `Content-Length` over chunked, `BrokenPipe`-safe `_safe_send_error`.
- socat readiness fail-fast (`READY=0` loop + `exit 1`) — your wrapper inherits it.
- shell_quote of `agent_id` / `project_dir` / `nono_profile` in the bash wrapper — already done in the synthesize function.

### Sanity checks before declaring done

```bash
# Drop into a paranoid codex sandbox shell
agent-sandbox run -a codex --sandbox-level paranoid -- bash

# 1. Scratch copy works (should show scratch contents, not your real ~/.codex)
ls -la ~/.codex/

# 2. Network is kernel-isolated (expected: connection failure, NOT 403 from proxy)
curl -s -o /dev/null https://attacker.com 2>&1

# 3. OpenAI API still works through the proxy
curl -s -x http://127.0.0.1:8118 https://api.openai.com/v1/models | head

# 4. Inner-sandbox conflict still resolved (codex's own --sandbox flag was disabled)
# verify by running codex normally and confirming it doesn't fail with bwrap-nesting errors

# 5. From the host, only ONE running socat per running agent; killing the agent removes it
pgrep -af 'socat.*8118'

# 6. Stale-socket cleanup works (only the live agent's socket; no leftovers)
ls ~/.agent-sandbox/proxy-*.sock 2>/dev/null
```

### Reference: the lince-98 commits that resolved each gotcha

- `077b37d3` — fragment lookup with agent prefix
- `9b214451` — auto-map ANTHROPIC_API_KEY in paranoid fragment
- `9142c367` — `--unshare-user --uid` to remap UID
- `a7933b48` — outer `unshare -U -n -r` wrapper instead of bwrap `--unshare-net`
- `9e62cf12` — proxy framing (Connection: close, no duplicate headers)
- `7f5898c4` — BrokenPipe handling in proxy
- `858fe521` — GH_TOKEN/GITHUB_TOKEN passthrough
- `405c3a11` / `5f987859` — review fixes (fail-fast socat, drop redundant `allow_domains`, dedupe shell_quote, stale-socket sweep)

Reading the diffs of those commits is faster than re-discovering the same problem from a stack trace.

## 2026-05-05 — implementation landed on branch `feature/lince-99-sandbox-levels-codex` (uncommitted, awaiting user manual test before push)

### Files
New:
- `lince-dashboard/nono-profiles/lince-codex-paranoid.json`
- `lince-dashboard/nono-profiles/lince-codex-permissive.json`
- `sandbox/profiles/codex-paranoid.toml`
- `sandbox/profiles/codex-permissive.toml`

Modified:
- `lince-dashboard/agents-defaults.toml` — collapsed `[agents.codex]` (legacy unsandboxed) + `[agents.codex-bwrap]` + `[agents.codex-nono]` into a single `[agents.codex]` with `sandbox_level="normal"` + `bwrap_conflict=true` + `disable_inner_sandbox_args=["--sandbox","danger-full-access"]`. Renamed legacy unsandboxed entry to `[agents.codex-unsandboxed]` (mirrors `claude-unsandboxed`). Removed the `[agents.codex-nono]` block from the nono-variants comment block. Added commented `[agents.codex-paranoid]` / `[agents.codex-permissive]` example blocks.
- `lince-dashboard/plugin/src/agent.rs::synthesize_sandboxed_command` — added `"codex"` arm to `inner_command` (with `--sandbox danger-full-access` baked in for the nono path), added `"codex" => ".codex"` to the `agent_home_subdir` match, and made the AgentSandbox branch always emit `--agent <base>` so codex/future-agents dispatch correctly (claude default is unchanged).
- `docs/documentation/dashboard/sandbox-levels.md` — new §7 “Per-agent specifics — codex” with per-level table, inner-sandbox-conflict note, OPENAI_API_KEY-per-level note, and bwrap-paranoid scratch-`~/.codex` limitation. Added OpenAI keystore commands to §6.

### Build / static checks
- `cargo build --target wasm32-wasip1` succeeds.
- All four new TOML/JSON files parse cleanly with python `tomllib`/`json`.
- agent-sandbox dry-run not exercised — no `~/.agent-sandbox/config.toml` on this host. AC #4 / #5 need runtime validation by the user.

### Notes / deviations from plan
- For bwrap paranoid, real `~/.codex` is still bind-mounted RW (no codex analog of `[claude] use_real_config = false`). Documented as a limitation in §7; recommendation is to use nono paranoid for the strongest codex isolation. The `home_rw_dirs` append-merge semantics of `merge_sandbox_level` make subtracting from the `[agents.codex]` `home_ro_dirs` impractical from a fragment.
- `_collect_proxy_rules` already handles unset `OPENAI_API_KEY` (silent drop), so the auto-mapping in `codex-paranoid.toml`'s `[env.extra]` is safe even without the host var set.
<!-- SECTION:NOTES:END -->
