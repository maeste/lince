---
id: LINCE-84
title: Dual-mode Codex agent — direct and bwrap-sandboxed variants
status: Done
assignee: []
created_date: '2026-03-25 13:50'
updated_date: '2026-03-25 14:08'
labels:
  - dashboard
  - sandbox
  - codex
  - multi-agent
milestone: m-12
dependencies:
  - LINCE-62
  - LINCE-83
references:
  - lince-dashboard/agents-defaults.toml
  - sandbox/agents-defaults.toml
  - sandbox/agent-sandbox
  - lince-dashboard/plugin/src/types.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Problem**: The current `codex` agent type runs Codex directly (`["codex", "--full-auto"]`), relying on Codex's own sandbox (which uses a different isolation model — not bwrap). The `bwrap_conflict = true` and `disable_inner_sandbox_args` fields in agents-defaults.toml are defined but **not actually used** since the command doesn't go through `agent-sandbox`.

Additionally, there's an inconsistency: `sandbox/agents-defaults.toml` says `disable_inner_sandbox_args = ["--no-sandbox"]` while `lince-dashboard/agents-defaults.toml` says `["--sandbox", "danger-full-access"]`. Need to verify which is correct.

**Context from testing**: When Codex runs via the current config, it operates in Codex's own sandbox (blocks /etc, $HOME writes, sets CODEX_SANDBOX_NETWORK_DISABLED=1) — a different runtime model than bubblewrap.

**Solution**: Offer two agent type variants:
- `codex` — runs directly, relies on Codex's own sandbox. Marked `sandboxed = true` (own sandbox). No profiles needed.
- `codex-bwrap` — runs through `agent-sandbox`, Codex's inner sandbox disabled. Uses bwrap for uniform isolation. Can use sandbox profiles.

**Implementation**:

1. **Keep existing `codex` agent type** as direct mode:
   - `command = ["codex", "--full-auto"]`
   - `sandboxed = true` (Codex's own sandbox)
   - `bwrap_conflict = false` (not relevant — not using bwrap)

2. **Add `codex-bwrap` agent type**:
   - `command = ["agent-sandbox", "run", "-p", "{project_dir}", "--id", "{agent_id}", "--agent", "codex"]`
   - `sandboxed = true` (bwrap sandbox)
   - `bwrap_conflict = true` (Codex uses bwrap internally)
   - Verify correct `disable_inner_sandbox_args` — likely `["--sandbox", "danger-full-access"]` based on Codex CLI docs (not `--no-sandbox`)
   - Profiles: inherit from discovered profiles (same as claude)

3. **Reconcile `disable_inner_sandbox_args`** between sandbox and dashboard agents-defaults.toml:
   - Research actual Codex CLI flag to disable its sandbox
   - Update both files to be consistent

4. **Update both `agents-defaults.toml` files** (dashboard + sandbox)

5. **Update documentation** to explain the two modes and when to use each
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Two codex agent types available: 'codex' (direct) and 'codex-bwrap' (agent-sandbox wrapped)
- [x] #2 codex direct mode relies on Codex's own sandbox, does not invoke agent-sandbox
- [x] #3 codex-bwrap mode routes through agent-sandbox with Codex inner sandbox disabled
- [x] #4 disable_inner_sandbox_args is consistent between sandbox/ and dashboard/ agents-defaults.toml
- [x] #5 codex-bwrap correctly disables Codex's internal sandbox via verified CLI flag
- [x] #6 Dashboard shows appropriate sandboxed indicator for both variants
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Split codex into `codex` (direct, own sandbox) and `codex-bwrap` (agent-sandbox wrapped). Fixed `disable_inner_sandbox_args` to `[\"--sandbox\", \"danger-full-access\"]` in both dashboard and sandbox configs. Direct mode has `profiles = []`, bwrap mode has `profiles = [\"__discover__\"]`.
<!-- SECTION:FINAL_SUMMARY:END -->
