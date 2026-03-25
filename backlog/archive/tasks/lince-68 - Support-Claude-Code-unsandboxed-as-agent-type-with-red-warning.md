---
id: LINCE-68
title: Support Claude Code unsandboxed as agent type with red warning
status: To Do
assignee: []
created_date: '2026-03-20 17:43'
labels:
  - agent-integration
  - claude
  - unsandboxed
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-58
  - LINCE-59
  - LINCE-60
  - LINCE-61
references:
  - lince-dashboard/plugin/src/config.rs
  - lince-dashboard/plugin/src/agent.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add "claude-unsandboxed" agent type that runs `claude` directly without `claude-sandbox` wrapper. This is the simplest multi-agent integration (same hooks, no sandbox complexity) and immediately useful for environments without bwrap or for quick testing.

**Why**: Users on systems without bwrap, or who trust the project, want to run Claude Code without sandbox overhead. A prominent red warning ensures this is a conscious security decision.

**Implementation**: Built-in default config for ClaudeUnsandboxed type with `command: ["env", "LINCE_AGENT_ID={agent_id}", "claude"]`, `sandboxed: false`, `pane_title_pattern: "claude"`, same `status_pipe_name: "claude-status"` (Claude native hooks work).

**Key file**: `plugin/src/config.rs` (default config entry)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 'Claude (unsandboxed)' appears in wizard agent type list
- [ ] #2 Spawns 'claude' directly without bwrap wrapper
- [ ] #3 Dashboard shows red warning indicator on agent row and detail panel
- [ ] #4 Claude native status hooks work (pipe 'claude-status')
- [ ] #5 Pane title correctly matches 'claude' pattern
<!-- AC:END -->
