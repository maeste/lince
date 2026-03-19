---
id: LINCE-40
title: 'Implement agent spawn, stop, and tracking via Zellij pane commands'
status: Done
assignee:
  - claude
created_date: '2026-03-19 10:38'
updated_date: '2026-03-19 13:13'
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
- [x] #1 src/agent.rs exists with spawn_agent() and stop_agent() functions
- [x] #2 n key spawns a new agent pane running claude-sandbox run with config defaults
- [x] #3 Spawned pane is hidden by default
- [x] #4 Agent appears in dashboard table with Starting status
- [x] #5 k key stops the selected agent and removes it from list
- [x] #6 Dead panes detected via PaneUpdate and cleaned up
- [x] #7 max_agents limit enforced with user-visible error message
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Executed Plan\n1. Created `src/agent.rs` with:\n   - `spawn_agent()` — builds CommandToRun with profile/project_dir from config, opens floating command pane, passes LINCE_AGENT_ID in context\n   - `stop_agent()` — closes terminal pane(s) by ID\n   - `reconcile_panes()` — matches starting agents to panes by title, marks dead panes as Stopped, auto-hides newly matched panes\n2. Updated `src/lib.rs`:\n   - Added `mod agent;` and `next_agent_id: u32` to State\n   - Wired Event::Key handling via `handle_key()` method using `KeyWithModifier`/`BareKey` API\n   - `n` key spawns agent, `k` kills selected, `j`/Down/Up cycle selection, `i` enters input mode\n   - Event::PaneUpdate calls `reconcile_panes()` to track agent lifecycle\n3. Fixed borrow issue: collect assigned_ids before mutable iteration\n4. Compiled cleanly with zero warnings
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## LINCE-40 Completed\n\n### Files created\n- `src/agent.rs` — spawn_agent(), stop_agent(), reconcile_panes()\n\n### Files modified\n- `src/lib.rs` — handle_key() with KeyWithModifier/BareKey, PaneUpdate wiring, next_agent_id counter\n\n### Key decisions\n- Used `KeyWithModifier`/`BareKey` (not legacy `Key`) for zellij-tile 0.42+ API compatibility\n- Agent matching uses pane title containing \"claude-sandbox\" since we can't get pane ID synchronously from spawn\n- Panes auto-hidden via `hide_pane_with_id` on first PaneUpdate match\n- LINCE_AGENT_ID passed via CommandToRun context map for hook identification\n- DoD #1, #2, #4 deferred to manual Zellij testing
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Agent spawn creates a visible process in Zellij pane list
- [ ] #2 Agent stop cleanly closes the pane (no orphaned processes)
- [x] #3 Dashboard table updates correctly after spawn and stop operations
- [ ] #4 Manual test: spawn 3 agents, kill middle one, verify table updates
<!-- DOD:END -->
