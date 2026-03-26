---
id: LINCE-62
title: 'Handle bwrap-conflicting agents (Codex, Claude Code) in sandbox'
status: Done
assignee: []
created_date: '2026-03-20 17:42'
updated_date: '2026-03-25 06:50'
labels:
  - sandbox
  - bwrap
  - compatibility
milestone: m-12
dependencies:
  - LINCE-57
references:
  - sandbox/claude-sandbox
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Some agents (Codex, Claude Code) use bwrap internally, which conflicts with the outer bwrap sandbox. The sandbox reads `bwrap_conflict` and `disable_inner_sandbox_args` from the agent's config entry and injects the appropriate flags automatically.

**Why**: Without this, agents with inner sandboxes will fail when wrapped in our bwrap sandbox due to nested namespace conflicts.

**Implementation scope**:
- When `bwrap_conflict: true` in agent config, append `disable_inner_sandbox_args` to the inner command
- Logic is fully generic — reads config fields, no per-agent code branches
- All agent-specific knowledge lives in `agents-defaults.toml` presets (e.g. codex gets `["--sandbox", "danger-full-access"]`, gemini gets `["--sandbox", "none"]`)
- Dry-run output confirms correct flag injection

**Key file**: `sandbox/claude-sandbox`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Agent config bwrap_conflict (bool) and disable_inner_sandbox_args (list) are read from config
- [x] #2 When bwrap_conflict=true, disable_inner_sandbox_args appended to inner command automatically
- [x] #3 Logic is generic — no per-agent code branches, purely config-driven
- [x] #4 Dry-run output confirms correct flag injection for any agent with bwrap_conflict=true
- [x] #5 Agents with bwrap_conflict=false run unchanged
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Already implemented as part of LINCE-57 refactor. resolve_agent_config() reads bwrap_conflict and disable_inner_sandbox_args from config, build_bwrap_cmd() appends them when bwrap_conflict=true. Verified via dry-run for codex (injected), gemini (not injected), opencode (not injected).
<!-- SECTION:NOTES:END -->
