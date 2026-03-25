---
id: LINCE-85
title: Dual-mode Gemini agent — direct and bwrap-sandboxed variants
status: Done
assignee: []
created_date: '2026-03-25 13:50'
updated_date: '2026-03-25 14:08'
labels:
  - dashboard
  - sandbox
  - gemini
  - multi-agent
milestone: m-12
dependencies:
  - LINCE-83
references:
  - lince-dashboard/agents-defaults.toml
  - sandbox/agents-defaults.toml
  - sandbox/agent-sandbox
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Problem**: The current `gemini` agent type runs Gemini CLI directly (`["gemini"]`). Gemini CLI has its own optional sandbox system (Docker/Podman/gVisor/Seatbelt) which is **disabled by default**. It does NOT use bwrap internally, so there is no bwrap nesting conflict.

**Context from research**:
- Gemini CLI sandbox is opt-in via `-s`/`--sandbox` flag or `GEMINI_SANDBOX` env var
- Sandboxing uses Docker/Podman/gVisor/Seatbelt — NOT bubblewrap
- Default is unsandboxed, so running inside bwrap is clean (no conflict)
- When inside bwrap, Gemini's own Docker-based sandbox would not work (no Docker inside bwrap), but that's fine since bwrap provides the isolation
- Current `disable_inner_sandbox_args = ["--sandbox", "none"]` in dashboard config — but Gemini has no `--sandbox none` flag. Since sandbox is off by default, no disable args are needed.

**Solution**: Offer two agent type variants:
- `gemini` — runs directly, no sandbox (Gemini's own sandbox is off by default). User can optionally enable Gemini's sandbox themselves.
- `gemini-bwrap` — runs through `agent-sandbox` with bwrap isolation. No inner sandbox conflict.

**Implementation**:

1. **Keep existing `gemini` agent type** as direct mode:
   - `command = ["gemini"]`
   - `sandboxed = false` (no sandbox by default)
   - `bwrap_conflict = false`

2. **Add `gemini-bwrap` agent type**:
   - `command = ["agent-sandbox", "run", "-p", "{project_dir}", "--id", "{agent_id}", "--agent", "gemini"]`
   - `sandboxed = true` (bwrap sandbox)
   - `bwrap_conflict = false` (Gemini doesn't use bwrap)
   - `disable_inner_sandbox_args = []` (sandbox off by default, nothing to disable)
   - Ensure `GEMINI_SANDBOX=false` in env_vars as a safety measure
   - Profiles: inherit from discovered profiles

3. **Fix current config**: Remove `disable_inner_sandbox_args = ["--sandbox", "none"]` since this flag doesn't exist in Gemini CLI

4. **Update both `agents-defaults.toml` files** (dashboard + sandbox)

5. **Ensure `GEMINI_API_KEY` passthrough** works in both modes
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Two gemini agent types available: 'gemini' (direct) and 'gemini-bwrap' (agent-sandbox wrapped)
- [x] #2 gemini direct mode runs without any sandbox by default
- [x] #3 gemini-bwrap mode routes through agent-sandbox with bwrap isolation
- [x] #4 No invalid --sandbox none flag passed to Gemini CLI
- [x] #5 GEMINI_API_KEY is correctly passed through in both modes
- [x] #6 Dashboard shows correct sandboxed/unsandboxed indicator for each variant
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Split gemini into `gemini` (direct, unsandboxed by default) and `gemini-bwrap` (agent-sandbox wrapped). Removed invalid `--sandbox none` flag. Added `GEMINI_API_KEY` passthrough in sandbox config. Direct mode marked `sandboxed = false`.
<!-- SECTION:FINAL_SUMMARY:END -->
