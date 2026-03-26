---
id: LINCE-86
title: Dual-mode OpenCode agent — direct and bwrap-sandboxed variants
status: Done
assignee: []
created_date: '2026-03-25 13:50'
updated_date: '2026-03-25 14:08'
labels:
  - dashboard
  - sandbox
  - opencode
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
**Problem**: The current `opencode` agent type runs OpenCode directly (`["opencode"]`). OpenCode has **no built-in sandbox** — only a UX permission system (allow/ask/deny rules in `opencode.json`) that is NOT a security boundary. It does NOT use bwrap internally, so wrapping in bwrap is clean.

**Context from research**:
- OpenCode has zero OS-level sandboxing — permissions are UX only
- Does not use bubblewrap, Docker, or any containerization
- No `--sandbox` or `--no-sandbox` CLI flags exist
- Running inside bwrap works without any conflicts
- There is a community `opencode-sandbox` npm plugin (uses bwrap on Linux) but it's not part of core OpenCode

**Solution**: Offer two agent type variants:
- `opencode` — runs directly, no sandbox at all. Unsandboxed warning shown in dashboard.
- `opencode-bwrap` — runs through `agent-sandbox` with bwrap isolation. No inner sandbox conflict.

**Implementation**:

1. **Update existing `opencode` agent type** as direct mode:
   - `command = ["opencode"]`
   - `sandboxed = false` (explicitly unsandboxed — OpenCode has no sandbox)
   - `bwrap_conflict = false`

2. **Add `opencode-bwrap` agent type**:
   - `command = ["agent-sandbox", "run", "-p", "{project_dir}", "--id", "{agent_id}", "--agent", "opencode"]`
   - `sandboxed = true` (bwrap sandbox)
   - `bwrap_conflict = false` (OpenCode doesn't use bwrap)
   - `disable_inner_sandbox_args = []` (nothing to disable)
   - Profiles: inherit from discovered profiles

3. **Update both `agents-defaults.toml` files** (dashboard + sandbox)

4. **Ensure correct home_ro_dirs** for OpenCode config (`~/.config/opencode/`)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Two opencode agent types available: 'opencode' (direct) and 'opencode-bwrap' (agent-sandbox wrapped)
- [x] #2 opencode direct mode runs without sandbox, dashboard shows UNSANDBOXED warning
- [x] #3 opencode-bwrap mode routes through agent-sandbox with bwrap isolation
- [x] #4 No invalid sandbox flags passed to OpenCode CLI
- [x] #5 OpenCode config directory (~/.config/opencode/) is accessible in bwrap mode
- [x] #6 Dashboard shows correct sandboxed/unsandboxed indicator for each variant
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Split opencode into `opencode` (direct, no sandbox) and `opencode-bwrap` (agent-sandbox wrapped). Added missing `[agents.opencode]` entry to sandbox agents-defaults.toml. Direct mode marked `sandboxed = false` with dashboard UNSANDBOXED warning.
<!-- SECTION:FINAL_SUMMARY:END -->
