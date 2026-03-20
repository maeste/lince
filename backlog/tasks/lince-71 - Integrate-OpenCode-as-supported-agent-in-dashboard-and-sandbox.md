---
id: LINCE-71
title: Integrate OpenCode as supported agent in dashboard and sandbox
status: To Do
assignee: []
created_date: '2026-03-20 17:44'
labels:
  - agent-integration
  - opencode
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-58
  - LINCE-59
  - LINCE-60
  - LINCE-61
  - LINCE-65
  - LINCE-66
references:
  - lince-dashboard/plugin/src/config.rs
  - sandbox/claude-sandbox
documentation:
  - 'https://github.com/opencode-ai/opencode'
  - 'https://opencode.ai/docs/permissions/'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Full integration of OpenCode. Dashboard config with built-in defaults. Sandbox agent config (no bwrap conflict — cleanest integration). Lifecycle wrapper for start/stop.

**Why**: OpenCode is a multi-provider Go agent with no sandbox conflicts. Easiest agent to integrate.

**Agent details** (from research):
- Invocation: `opencode` (TUI) or `opencode run --agent <name> "prompt"` (headless)
- Config dir: `~/.config/opencode/` (ro-bind needed)
- API keys: Multi-provider (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
- bwrap conflict: NONE — no built-in sandbox, single Go binary
- No native hooks — use `lince-agent-wrapper`

**Key files**: `plugin/src/config.rs`, `sandbox/claude-sandbox` config
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 OpenCode appears in wizard agent type list
- [ ] #2 Spawns both sandboxed (bwrap) and unsandboxed
- [ ] #3 Status shows Started/Stopped via lince-agent-wrapper lifecycle
- [ ] #4 ~/.config/opencode/ exposed read-only in sandbox
- [ ] #5 Multi-provider API keys configurable via env passthrough
- [ ] #6 Pane title matches correctly for OpenCode
<!-- AC:END -->
