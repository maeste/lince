---
id: LINCE-40
title: 'Implement agent spawn, stop, and tracking via Zellij pane commands'
status: To Do
assignee: []
created_date: '2026-03-19 10:38'
labels:
  - dashboard
  - agent
  - rust
milestone: m-10
dependencies:
  - LINCE-37
  - LINCE-38
references:
  - >-
    sandbox/claude-sandbox (CLI: lines 905-921 for argparse, run subcommand at
    line 543)
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Spawn, stop, and track Claude Code agent instances as Zellij panes. Each agent runs `claude-sandbox run` with configurable parameters. The sandbox module (`sandbox/claude-sandbox`) handles all isolation — this task only manages pane lifecycle.

## Implementation Plan

1. Create `src/agent.rs`
2. **Spawn — single pane mode**:
   - `open_command_pane_floating(CommandToRun { path: config.sandbox_command, args: ["run", "-P", profile, "-p", project_dir], cwd: project_dir }, FloatingPaneCoordinates::default())`
   - Immediately hide: `hide_pane_with_id(pane_id)` (agents hidden by default)
   - Create `AgentInfo` with status `Starting`, store in `State.agents`
   - Auto-assign ID: `"agent-{n}"` with incrementing counter
   - Set `LINCE_AGENT_ID` env var so hooks can identify the agent
3. **Spawn — multi pane mode**:
   - `new_tab_with_layout(layout_string)` using agent-multi KDL template with command/args substituted
   - Track all pane IDs from the new tab
4. **Stop**: `close_terminal_pane(pane_id)` for each pane, remove from `State.agents`
5. **Track**:
   - On `Event::PaneUpdate(pane_manifest)`: check pane_ids still exist, mark missing as `Stopped`
   - On `Event::CommandPaneOpened { terminal_pane_id }`: match to pending spawns, update `pane_id`
6. **Key handling**: `n` → spawn with defaults, `k` → stop selected agent
7. Enforce `config.max_agents` with error message in command bar
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 src/agent.rs exists with spawn_agent() and stop_agent() functions
- [ ] #2 n key spawns a new agent pane running claude-sandbox run with config defaults
- [ ] #3 Spawned pane is hidden by default
- [ ] #4 Agent appears in dashboard table with Starting status
- [ ] #5 k key stops the selected agent and removes it from list
- [ ] #6 Dead panes detected via PaneUpdate and cleaned up
- [ ] #7 max_agents limit enforced with user-visible error message
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Agent spawn creates a visible process in Zellij pane list
- [ ] #2 Agent stop cleanly closes the pane (no orphaned processes)
- [ ] #3 Dashboard table updates correctly after spawn and stop operations
- [ ] #4 Manual test: spawn 3 agents, kill middle one, verify table updates
<!-- DOD:END -->
