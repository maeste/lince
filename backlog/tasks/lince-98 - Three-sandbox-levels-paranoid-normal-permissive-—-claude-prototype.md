---
id: LINCE-98
title: Three sandbox levels (paranoid/normal/permissive) — claude prototype
status: To Do
assignee: []
created_date: '2026-05-04 20:32'
updated_date: '2026-05-04 20:53'
labels:
  - sandbox
  - lince-dashboard
  - prototype
milestone: m-13
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/48'
  - 'https://github.com/RisorseArtificiali/lince/issues/47'
  - lince-dashboard/agents-defaults.toml
  - lince-dashboard/nono-profiles/lince-claude.json
  - sandbox/agent-sandbox
  - sandbox/config.toml.example
documentation:
  - 'https://nono.sh/docs/cli/features/networking.md'
  - 'https://nono.sh/docs/cli/features/credential-injection.md'
  - 'https://nono.sh/docs/cli/features/profile-authoring.md'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Goal

Implement the three-level sandbox model (paranoid/normal/permissive) on **claude** as the canonical prototype. The runtime dispatch logic, sandbox-policy mechanism, and TOML schema introduced here are reused by the codex/gemini/opencode/pi follow-up tasks.

Tracks GH issue [#48](https://github.com/RisorseArtificiali/lince/issues/48). Umbrella: [#47](https://github.com/RisorseArtificiali/lince/issues/47).

## Background — full design context (no need to re-brainstorm)

LINCE today exposes `[agents.claude]` (bwrap), `[agents.claude-unsandboxed]`, `[agents.claude-nono]` as separate entries; the N-picker shows all three. Decision: collapse to a **single** `[agents.claude]` driven by two new attributes:

- `sandbox_level = "paranoid" | "normal" | "permissive"` — default `"normal"`
- `sandbox_backend = "bwrap" | "nono"` — default per OS (linux=bwrap, mac=nono); explicit override allowed

`[agents.claude-unsandboxed]` stays as a separate entry (opt-out, not a level). Alternative levels appear as **commented templates** in agents-defaults.toml so the picker stays uncluttered while remaining self-discoverable.

## Three levels — claude specifics

LLM provider for proxy/credential injection: **anthropic** (nono keystore account: `anthropic_api_key`).

| | paranoid | normal | permissive |
|---|---|---|---|
| nono `network` | `credentials: ["anthropic"]` (proxy LLM only, blocks the rest) | inherited from `claude-code` preset | `network_profile: "developer"` + `allow_domain: ["api.github.com","github.com","objects.githubusercontent.com"]` + `credentials: ["anthropic"]` |
| nono `filesystem` | `$WORKDIR` rw + scratch copy of `~/.claude` (rsync pre-launch) | as today (`lince-claude.json`) | + `~/.config/gh` r, `~/.cache` r, `~/.ssh/known_hosts` r |
| bwrap `[claude]` | `use_real_config = false` forced + no-network | as today (default) | + bind-read of `~/.config/gh`, `~/.cache`, `~/.ssh/known_hosts` |
| Tools | — | — | `gh` CLI (no docker, no podman, no `git push` — push goes via gh) |

**Out of scope (deliberately excluded)**: docker, podman, direct `git push`.

## nono native features used (no need to reinvent)

- `network.block: true` — full lockdown
- `network.credentials: [...]` — LLM proxy with credential injection from system keystore (or 1Password / Apple Passwords)
- `network.network_profile: "developer"` + `allow_domain: [...]` — permissive allowlist
- nono profile inheritance (`extends: "claude-code"`)

## File touch list

**New:**
- `lince-dashboard/nono-profiles/lince-claude-paranoid.json`
- `lince-dashboard/nono-profiles/lince-claude-permissive.json`
- `sandbox/profiles/claude-paranoid.toml` (built-in, format depends on R1)
- `sandbox/profiles/claude-permissive.toml` (built-in)

**Modified:**
- `lince-dashboard/agents-defaults.toml` — single `[agents.claude]` with `sandbox_level`/`sandbox_backend` + commented templates for paranoid/permissive; remove `[agents.claude-nono]`
- `lince-dashboard/plugin/src/...` — read both attributes, dispatch to right profile/command; auto-default backend per OS
- `sandbox/agent-sandbox` — support sandbox-policy profiles (or layer on top of `[claude]` config section) — see R1
- `lince-dashboard/install.sh` — copy new nono profiles, idempotent

## Wizard "N" behavior

The N-picker shows only **uncommented** entries. Users opt into non-default levels by uncommenting alternative `[agents.X]` blocks shipped as commented templates. **No plugin changes for the picker itself.**

## Research items (resolve during execution, not blockers)

- **R1** Does `agent-sandbox` already have a sandbox-policy profile mechanism? Today `[profiles.*]` in `sandbox/config.toml` = LLM credential injection, not filesystem/network policy. Either add policy profiles or layer paranoid/permissive on top of `[claude]` section.
- **R2** "Scratch copy" of `~/.claude` under nono: pre-spawn rsync hook in lince-dashboard plugin (rsync to `$XDG_RUNTIME_DIR/lince-<agent-id>/.claude`, set HOME or bind mount), or built into nono profile activation?
- **R3** bwrap: existing `--no-network` or equivalent for paranoid, or do we need to add it?
- **R4** Permissive allowlist for MCP servers running over internet (Context7, Sequential, etc.) — opt-in or default?

## Out of scope for this task

- codex, gemini, opencode, pi (covered by separate follow-up tasks/issues)
- docker/podman in permissive
- direct `git push`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agents-defaults.toml has a single [agents.claude] with sandbox_level/sandbox_backend; claude-nono removed; claude-unsandboxed kept
- [ ] #2 sandbox_level=paranoid on nono: arbitrary outbound network fails (curl https://example.com), Claude Code reaches Anthropic API via proxy, modifications to ~/.claude inside sandbox stay isolated from real ~/.claude
- [ ] #3 sandbox_level=permissive on nono: gh auth status works, gh pr create works, docker ps fails, direct git push fails (use gh)
- [ ] #4 N-picker shows 'Claude Code' once (not three times)
- [ ] #5 Default backend per OS works (linux=bwrap, mac=nono); explicit sandbox_backend=nono on linux works
- [ ] #6 install.sh copies new nono profiles idempotently and is safe to re-run
- [ ] #7 Manual test doc in docs/ covering each (level x backend) cell
- [ ] #8 Documentation page created (e.g. docs/documentation/dashboard/sandbox-levels.md) covering: what each of paranoid/normal/permissive does, how to choose, backend selection, customization mechanism
- [ ] #9 Doc explicitly states sandbox_level is a free-form profile suffix (not a closed enum); the three shipped levels are opinionated examples
- [ ] #10 Doc includes a worked customization example (e.g. lince-claude-with-aws.json) showing file location, naming convention, extends, and how to enable via config.toml
- [ ] #11 Plugin accepts any sandbox_level value: well-known names get shipped profiles; arbitrary names resolved by file lookup with clear error if profile missing
- [ ] #12 lince-dashboard/README.md and agents-defaults.toml header comment cross-link to the new doc page
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation plan — lince-98 (claude prototype)

> Sequencing rationale: research items first (Phase 0) because their answers shape the code in Phases 1–3. The schema + dispatch (Phase 1) is the load-bearing piece; subsequent phases are decoupled file work.

### Phase 0 — Research (resolve R1–R4)

Concrete artifacts: a short markdown note inside this task's notes (via `notesAppend`) capturing the answers, so follow-up tasks (lince-99..102) inherit the resolved decisions without re-investigation.

- **R1** Read `sandbox/agent-sandbox` (Python single-file). Inspect: existing `[claude]` / `[codex]` / `[gemini]` / `[opencode]` / `[pi]` config sections, `resolve_profiles()`, `generate_nono_profile()`. Decide ONE of:
  - **(a)** Add new `[sandbox_policies.NAME]` table type that layers on top of agent sections
  - **(b)** Reuse existing `[claude]` etc. and pass `--sandbox-level NAME` flag that toggles a few keys at runtime
  - **(c)** Ship presets as TOML fragments under `sandbox/profiles/` and the script merges them into the resolved `[claude]` section
  
  Bias toward (c) — minimal new abstraction, easy to ship as built-in.
- **R2** Read `lince-dashboard/plugin/src/agent.rs` (or wherever `open_command_pane` is invoked). Decide where the scratch copy of `~/.claude` happens for nono paranoid:
  - Option A: pre-spawn step in plugin (Rust): `run_command(["rsync", "-a", "~/.claude/", "$XDG_RUNTIME_DIR/lince-<id>/.claude/"])` then bind into nono profile via `$HOME` override
  - Option B: nono profile activation hook (if nono supports pre/post hooks)
  - Option C: shell wrapper in the `command` field
  
  Bias toward A (Option C is brittle, Option B unverified). For bwrap, this is **already solved** by `use_real_config = false` (default).
- **R3** Inspect `agent-sandbox` for existing network-disable flag. Search for `unshare`, `--unshare-net`, `--share-net`, `--no-network` in the script. If none, add `--no-network` flag that toggles bwrap's `--unshare-net`. Document the result in notes.
- **R4** Catalog: which MCP servers (Context7, Sequential, Magic, Playwright, Tavily, Serena, Morphllm) call out to internet from inside the agent? Decision tree:
  - If MCP runs **outside** the sandbox (host process), no allowlist needed
  - If MCP runs **inside** the sandbox (Claude Code spawns it), permissive must allow its endpoints
  - For prototype: **permissive does NOT auto-allow MCP endpoints**. Document that MCP-on-internet users need a custom profile (`lince-claude-permissive-with-mcp.json`).

### Phase 1 — Plugin schema + dispatch

**File:** `lince-dashboard/plugin/src/config.rs` (or wherever `AgentConfig` is defined; grep for `sandboxed: bool` to find it).

1. Add fields to the agent config struct:
   ```rust
   pub sandbox_level: Option<String>,      // default: Some("normal")
   pub sandbox_backend: Option<String>,    // default: per OS (see fn below)
   ```
2. Default-resolution helper:
   ```rust
   fn default_backend() -> &'static str {
       if cfg!(target_os = "macos") { "nono" } else { "bwrap" }
   }
   ```
3. Profile-resolution helper (free-form, not enum):
   ```rust
   fn resolve_nono_profile(agent: &str, level: &str) -> String {
       if level == "normal" { format!("lince-{}", agent) }
       else { format!("lince-{}-{}", agent, level) }
   }
   ```
4. **Command generation**: today the entries hardcode `command = ["nono", "run", "--profile", "lince-claude", ...]` etc. Replace this for entries that opt into the new model: when `sandbox_level` is present, the plugin **overrides** the static `command` with one generated from the (level, backend) pair. Concretely:
   - bwrap: `["agent-sandbox", "run", "-p", "{project_dir}", "--id", "{agent_id}", "--sandbox-level", level, ...]` (assumes Phase 0 R1/R3 result)
   - nono: `["nono", "run", "--profile", resolve_nono_profile(agent, level), "--workdir", "{project_dir}", "--", "claude", "--dangerously-skip-permissions"]`
5. **Profile-file existence check** at agent spawn time. If the resolved profile does not exist (nono profile JSON missing, or bwrap profile fragment missing), surface a user-visible error in the dashboard pane title or a short pop-up. **Do not silently fall back.**
6. **Unit test**: add a test in `plugin/src/config.rs` (or sibling test file) covering `resolve_nono_profile()` for `normal` / `paranoid` / arbitrary `with-aws`.

### Phase 2 — Scratch copy of `~/.claude` for paranoid (R2 → Option A)

**File:** `lince-dashboard/plugin/src/agent.rs`

1. New helper `prepare_paranoid_scratch(agent_id: &str, agent_name: &str) -> PathBuf`:
   - Computes scratch dir: `$XDG_RUNTIME_DIR/lince-{agent_id}` (fallback `/tmp/lince-{agent_id}`)
   - Determines source `~/.claude/` for claude (data-driven from `agents-defaults.toml` `home_ro_dirs[0]`)
   - Calls `run_command(["rsync", "-a", "--delete", source, dest])` async, returns dest path
   - Returns the scratch path
2. Spawn flow: when `sandbox_level == "paranoid"`, before `open_command_pane`, call `prepare_paranoid_scratch()`. Wait for completion event, then spawn the pane with `HOME` env overridden to the scratch dir.
3. **Cleanup**: on agent stop event, remove the scratch dir (best-effort, log on failure). Tie into the existing agent-stop pipeline (search `Event::PaneClosed` or similar).
4. **bwrap path**: no Phase 2 work needed — `use_real_config = false` (default in `sandbox/`) already handles this. Document the asymmetry in the doc page.

### Phase 3 — Build sandbox profiles

**Nono profiles** (`lince-dashboard/nono-profiles/`):

`lince-claude-paranoid.json`:
```json
{
  "extends": "lince-claude",
  "meta": { "name": "lince-claude-paranoid", "description": "claude — network locked except Anthropic API via proxy; ~/.claude isolated scratch" },
  "filesystem": {
    "allow": ["$WORKDIR"],
    "read": []
  },
  "network": {
    "credentials": ["anthropic"]
  }
}
```

`lince-claude-permissive.json`:
```json
{
  "extends": "lince-claude",
  "meta": { "name": "lince-claude-permissive", "description": "claude — github + gh CLI access; ~/.config/gh, ~/.cache, ~/.ssh/known_hosts readable" },
  "filesystem": {
    "allow": ["$WORKDIR"],
    "read": ["$HOME/.config/gh", "$HOME/.cache", "$HOME/.ssh/known_hosts", "$HOME/.local/lib"]
  },
  "network": {
    "network_profile": "developer",
    "credentials": ["anthropic"],
    "allow_domain": ["api.github.com", "github.com", "objects.githubusercontent.com"]
  }
}
```

**Bwrap profiles** (`sandbox/profiles/`) — final form depends on Phase 0 R1. Sketch (Option c):

`claude-paranoid.toml`:
```toml
# Layered on top of [claude] when sandbox_level = "paranoid"
[claude]
use_real_config = false   # forced (overrides user override)
[sandbox]
network = false            # (R3-dependent key name)
```

`claude-permissive.toml`:
```toml
[claude]
extra_ro_binds = ["~/.config/gh", "~/.cache", "~/.ssh/known_hosts"]
[sandbox]
network = true
```

### Phase 4 — agents-defaults.toml

**File:** `lince-dashboard/agents-defaults.toml`

1. Replace lines 15–25 (current `[agents.claude]`) with:
   ```toml
   [agents.claude]
   command = ["agent-sandbox", "run", "-p", "{project_dir}", "--id", "{agent_id}"]   # overridden by plugin when sandbox_level set
   pane_title_pattern = "agent-sandbox"
   status_pipe_name = "claude-status"
   display_name = "Claude Code"
   short_label = "CLA"
   color = "blue"
   sandboxed = true
   has_native_hooks = true
   home_ro_dirs = ["~/.claude/"]
   profiles = ["__discover__"]
   sandbox_level = "normal"          # paranoid | normal | permissive (or any custom — see docs)
   # sandbox_backend = "bwrap"       # default per OS; uncomment to override
   
   # Alternative levels — uncomment ONE [agents.claude-XXX] block below to opt into paranoid or permissive.
   # See docs/documentation/dashboard/sandbox-levels.md for what each level does and how to customize.
   #
   # [agents.claude-paranoid]
   # ...same as [agents.claude] but with sandbox_level = "paranoid"...
   #
   # [agents.claude-permissive]
   # ...same as [agents.claude] but with sandbox_level = "permissive"...
   ```
2. Remove lines 134–145 (`[agents.claude-nono]`) — its functionality is now `sandbox_backend = "nono"` on `[agents.claude]`.
3. Keep lines 27–36 (`[agents.claude-unsandboxed]`) untouched — it's a separate opt-out path.
4. Update header comment (lines 1–13) to point readers to `docs/documentation/dashboard/sandbox-levels.md`.

### Phase 5 — install.sh / update.sh

**Files:** `lince-dashboard/install.sh`, `lince-dashboard/update.sh`

1. Step 10 (nono profiles): the existing `for profile in "$NONO_PROFILES_SRC"/lince-*.json` glob already picks up the two new files. Verify it matches the new naming (`lince-claude-paranoid.json`, `lince-claude-permissive.json`).
2. Add a printed reminder after profile install (only if nono is detected as installed) telling the user to populate the keystore for paranoid level:
   ```
   For paranoid sandbox level: populate the nono keystore with your Anthropic key:
     security add-generic-password -s "nono" -a "anthropic_api_key" -w "sk-ant-..."     # macOS
     # or use 1Password / Apple Passwords integration; see https://nono.sh/docs/cli/features/credential-injection.md
   ```
3. update.sh: mirror the profile copy (same loop pattern). No interactive step needed for these — they're per-agent profiles, not user-config.
4. Verify idempotency by running `install.sh` twice in a clean clone; second run prints no new copies.

### Phase 6 — Documentation

**File:** `docs/documentation/dashboard/sandbox-levels.md` (new)

Sections (rough headings):
1. **Overview** — one paragraph: what sandboxing buys you, the three shipped levels at a glance
2. **Levels in detail** — for each of `paranoid` / `normal` / `permissive`:
   - Network policy (English + nono JSON snippet + bwrap equivalent)
   - Filesystem policy
   - Tools available / unavailable
   - "What does Claude Code see / fail to do" worked example
3. **How to choose** — short decision guide with trade-offs
4. **Backend selection** — `sandbox_backend = "bwrap" | "nono"`, default per OS, when to override (Linux user wanting Landlock-based isolation, etc.)
5. **Customization** — *prominent* section:
   - `sandbox_level` is a free-form profile suffix; the three shipped names are opinionated examples
   - File location convention: `~/.config/nono/profiles/lince-{agent}-{name}.json`, `sandbox/profiles/{agent}-{name}.toml`
   - `extends` mechanism for nono profiles
   - **Worked example**: `lince-claude-with-aws.json` (full JSON shown above in implementation notes)
   - How to enable: `[agents.claude] sandbox_level = "with-aws"` in `~/.config/lince-dashboard/config.toml`
   - How to verify: command to run inside the sandbox to confirm allowlist works
6. **Keystore setup** — short section pointing to nono docs for populating the keystore
7. **Future work** — link to GH #53 (wizard UX) so readers know there's more coming

**Cross-links to add:**
- `lince-dashboard/README.md`: 3–4 lines summary + link
- `lince-dashboard/agents-defaults.toml` header comment: one-line link

### Phase 7 — Manual test plan

**File:** `docs/documentation/dashboard/sandbox-levels-testing.md` (new) — explicit manual checklist.

Cells (level × backend):

| | bwrap (linux) | nono (linux) | nono (macOS) |
|---|---|---|---|
| paranoid | ✅ test | ✅ test | ✅ test (if mac available) |
| normal | ✅ test (regression) | ✅ test (regression) | ✅ test (regression) |
| permissive | ✅ test | ✅ test | ✅ test (if mac available) |

Per cell, the doc spells out the commands to run from inside the agent and the expected outcome:
- paranoid: `curl https://example.com` → fails; Claude Code chat works; `ls ~/.claude` shows isolated copy
- normal: existing behavior unchanged (smoke test)
- permissive: `gh auth status` → success; `gh pr create` → success (with token); `docker ps` → fails; direct `git push origin HEAD` → fails

### Phase 8 — Branch / PR / merge

1. Branch: `feature/lince-98-sandbox-levels-claude` from `upstream/main`
2. Commits: prefer multiple small commits per phase (easier review):
   - `dashboard: add sandbox_level/sandbox_backend fields to AgentConfig`
   - `dashboard: paranoid scratch copy of agent home dir for nono`
   - `nono-profiles: add claude-paranoid and claude-permissive`
   - `sandbox: add claude-paranoid/permissive policy fragments` (Phase 0 R1 result)
   - `agents-defaults: collapse claude/claude-nono into single entry`
   - `install: ship new nono profiles + keystore reminder`
   - `docs: sandbox-levels page + manual test plan`
3. PR title: `dashboard: three-level sandbox per agent (paranoid/normal/permissive) — claude prototype`
4. PR body: link issue #48, summary by phase, screenshots if N-picker UX changed at all, manual test results table

### Verification before declaring done

Run all 7 acceptance criteria from the task header. The test plan doc (Phase 7) is the executable form of those.

### Risks / known unknowns

- **Phase 0 R1 outcome may force schema redesign.** If `agent-sandbox` cannot reasonably accept layered policy fragments, fall back to passing CLI flags from the plugin (e.g. `--sandbox-level paranoid`) and have agent-sandbox read them. Either way, isolate the change to a new module so follow-up tasks can lift it cleanly.
- **MCP-on-internet for permissive (R4)** is deliberately out of scope. Users who hit this can write a custom profile — already covered by the customization story.
- **Scratch copy size** — `~/.claude` can be large (skill caches, MCP downloads). rsync should be fast on local FS but log timing if > 1s and consider only copying the subset claude actually needs (settings + skills, not caches). Decide during Phase 2 implementation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Documentation requirements (added after design review)

The task **must** ship documentation as part of the prototype. The doc establishes structure that the codex/gemini/opencode/pi follow-ups extend with their own agent-specific entries.

### Where the doc lives

- New page: `docs/documentation/dashboard/sandbox-levels.md` (or extend an existing page if it fits — TBD during execution)
- Cross-link from `lince-dashboard/README.md` (a 3–4 line summary + link)
- Cross-link from `agents-defaults.toml` header comment (point to the doc URL/path for full explanation)

### Doc content checklist

1. **What the three levels mean** — for each of `paranoid` / `normal` / `permissive`:
   - Network policy (in plain English, then the concrete `network.*` JSON snippet for nono and the equivalent in bwrap)
   - Filesystem policy (paths granted/denied, scratch-copy behavior)
   - Tools available (gh, etc.) and tools deliberately *not* available (docker, podman, direct git push)
   - Concrete worked example: "what does Claude Code see / fail to do in this level?"
2. **How to choose a level** — short decision guide (e.g. "use paranoid for untrusted prompts or new agents; normal for daily work; permissive when you need gh push and don't mind broader filesystem read"). Be honest about trade-offs.
3. **Backend selection** — `sandbox_backend = "bwrap" | "nono"`, default per OS, when to override.
4. **Customization is supported** — these three are **opinionated examples**, not a closed enum.

### Customization mechanism (architecture clarification)

`sandbox_level` is treated by the plugin as the **suffix of the profile name**, not as a closed enum:

- nono: `sandbox_level = "X"` → looks for `~/.config/nono/profiles/lince-{agent}-{X}.json` (falls back to `lince-{agent}.json` if `X = "normal"`)
- bwrap: `sandbox_level = "X"` → looks for `sandbox/profiles/{agent}-{X}.toml`

The plugin **must** accept any string for `sandbox_level` (well-known names `paranoid|normal|permissive` get the shipped profiles; any other name is resolved by file lookup, with a clear error message if the profile file is missing).

### Worked customization example to include in the doc

Walk the user through creating `lince-claude-with-aws.json`:

```json
{
  "extends": "lince-claude",
  "meta": { "name": "lince-claude-with-aws", "description": "claude + AWS Bedrock access" },
  "filesystem": {
    "allow": ["$WORKDIR"],
    "read": ["$HOME/.aws"]
  },
  "network": {
    "credentials": ["anthropic"],
    "allow_domain": ["bedrock-runtime.us-east-1.amazonaws.com"]
  }
}
```

Then in `~/.config/lince-dashboard/config.toml`:
```toml
[agents.claude]
sandbox_level = "with-aws"
```

Show: file location, naming convention, `extends`, what each addition grants, and how to verify it works.

Mention that the same applies to bwrap profiles (`sandbox/profiles/claude-with-aws.toml`).

### What the follow-up tasks (lince-99..102) inherit

The follow-up agent tasks **do not re-invent** this doc structure. Each of them:
- Adds its agent-specific row to the level-comparison table
- Documents agent-specific quirks (e.g. codex inner-sandbox conflict, opencode Bun/Landlock, pi multi-provider)
- Does **not** re-explain the overall mechanism — that lives in the master doc page from this task
<!-- SECTION:NOTES:END -->
