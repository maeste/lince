---
id: LINCE-69
title: Integrate Codex CLI as supported agent in dashboard and sandbox
status: To Do
assignee: []
created_date: '2026-03-20 17:43'
labels:
  - agent-integration
  - codex
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-58
  - LINCE-59
  - LINCE-60
  - LINCE-61
  - LINCE-62
  - LINCE-65
references:
  - lince-dashboard/plugin/src/config.rs
  - sandbox/claude-sandbox
documentation:
  - 'https://developers.openai.com/codex/cli/reference'
  - 'https://developers.openai.com/codex/concepts/sandboxing'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Full integration of OpenAI Codex CLI. Dashboard config with built-in defaults. Sandbox agent config with bwrap conflict handling (`--sandbox danger-full-access`). Lifecycle wrapper for start/stop status.

**Why**: Codex CLI is a major alternative coding agent. Supporting it expands the dashboard to a true multi-agent hub.

**Agent details** (from research):
- Invocation: `codex` (interactive) or `codex exec "prompt"` (headless)
- Key flags: `--sandbox danger-full-access` (disable inner bwrap), `--full-auto`
- Config dir: `~/.codex/` (ro-bind needed)
- API key: `OPENAI_API_KEY`
- bwrap conflict: HIGH — uses bwrap internally, must disable with `--sandbox danger-full-access`
- No native hooks — use `lince-agent-wrapper` for lifecycle status

**Key files**: `plugin/src/config.rs`, `sandbox/claude-sandbox` config
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Codex appears in wizard agent type list
- [ ] #2 Spawns inside bwrap sandbox with --sandbox danger-full-access auto-injected
- [ ] #3 Status shows Started/Stopped via lince-agent-wrapper lifecycle
- [ ] #4 OPENAI_API_KEY passed through to sandbox
- [ ] #5 ~/.codex/ exposed read-only in sandbox
- [ ] #6 Pane title matches correctly for Codex
<!-- AC:END -->
