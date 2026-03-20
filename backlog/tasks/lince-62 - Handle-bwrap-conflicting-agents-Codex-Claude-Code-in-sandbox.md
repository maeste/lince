---
id: LINCE-62
title: 'Handle bwrap-conflicting agents (Codex, Claude Code) in sandbox'
status: To Do
assignee: []
created_date: '2026-03-20 17:42'
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
Codex CLI and Claude Code use bwrap internally, which conflicts with the outer bwrap sandbox (nested user namespaces may fail). Add `bwrap_conflict` and `disable_inner_sandbox_args` fields to per-agent config. When running inside bwrap, inject the appropriate flags to disable the inner sandbox.

**Why**: Without this, Codex and Claude Code will fail when wrapped in our bwrap sandbox due to nested namespace conflicts.

**Key agents affected**:
- Codex: inject `--sandbox danger-full-access`
- Gemini: inject flag to disable Docker sandbox (no Docker socket in bwrap)
- OpenCode: no conflict, no changes
- Claude Code: already handled by existing architecture

**Key file**: `sandbox/claude-sandbox`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Agent config has bwrap_conflict (bool) and disable_inner_sandbox_args (list) fields
- [ ] #2 Codex inside bwrap gets --sandbox danger-full-access appended automatically
- [ ] #3 Gemini inside bwrap gets Docker sandbox disabled
- [ ] #4 OpenCode runs unchanged (no inner sandbox)
- [ ] #5 Dry-run output confirms correct flag injection for each agent
<!-- AC:END -->
