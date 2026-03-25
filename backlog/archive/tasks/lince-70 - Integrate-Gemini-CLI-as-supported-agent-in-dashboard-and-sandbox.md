---
id: LINCE-70
title: Integrate Gemini CLI as supported agent in dashboard and sandbox
status: To Do
assignee: []
created_date: '2026-03-20 17:43'
labels:
  - agent-integration
  - gemini
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-58
  - LINCE-59
  - LINCE-60
  - LINCE-61
  - LINCE-62
  - LINCE-65
  - LINCE-66
references:
  - lince-dashboard/plugin/src/config.rs
  - sandbox/claude-sandbox
documentation:
  - 'https://github.com/google-gemini/gemini-cli'
  - 'https://geminicli.com/docs/cli/sandbox/'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Full integration of Google Gemini CLI. Dashboard config with built-in defaults. Sandbox agent config with Docker sandbox disabled (no Docker inside bwrap). Lifecycle wrapper for start/stop.

**Why**: Gemini CLI is Google's coding agent. Supporting it provides multi-vendor choice.

**Agent details** (from research):
- Invocation: `gemini` (interactive) or `gemini -p "prompt"` (headless)
- Key flags: `--sandbox` (Docker-based, must disable in bwrap), `--yolo` (auto-approve)
- Config dir: `~/.gemini/` (ro-bind needed)
- API key: `GEMINI_API_KEY`
- bwrap conflict: LOW — Docker sandbox irrelevant inside bwrap, just disable
- No native hooks — use `lince-agent-wrapper`

**Key files**: `plugin/src/config.rs`, `sandbox/claude-sandbox` config
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Gemini appears in wizard agent type list
- [ ] #2 Spawns inside bwrap sandbox with Docker sandbox disabled
- [ ] #3 Status shows Started/Stopped via lince-agent-wrapper lifecycle
- [ ] #4 GEMINI_API_KEY passed through to sandbox
- [ ] #5 ~/.gemini/ exposed read-only in sandbox
- [ ] #6 Pane title matches correctly for Gemini
<!-- AC:END -->
