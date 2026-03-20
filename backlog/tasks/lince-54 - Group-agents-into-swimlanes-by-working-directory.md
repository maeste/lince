---
id: LINCE-54
title: Group agents into swimlanes by working directory
status: Done
assignee: []
created_date: '2026-03-19 22:07'
updated_date: '2026-03-20 08:58'
labels:
  - dashboard
  - ui
  - enhancement
milestone: m-11
dependencies:
  - LINCE-48
references:
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/dashboard.rs
  - lince-dashboard/plugin/src/types.rs
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The dashboard currently shows agents in a flat list. When agents are spawned across different working directories (via wizard or templates), there is no visual grouping — the user cannot quickly see which agents belong to which project.

## Problem

Agents have a `project_dir` field set at spawn time, but the dashboard renders them in a single flat table. The existing `group: Option<String>` field (set from template names) was intended for grouping but doesn't reflect project-based organization. Users working on multiple projects simultaneously need visual separation.

## Design Decisions

- **Group by `project_dir`, not `group`**: The `project_dir` field is always set and represents the actual workspace. Template `group` becomes a sub-label on the agent name row instead.
- **Swimlane headers**: Each unique `project_dir` gets a colored header row in the agent list. Headers show a shortened path (e.g., `~/project/lince` instead of `/home/user/project/lince`).
- **Sorted within swimlanes**: Agents within each swimlane are sorted by name/ID for stable ordering.
- **Selection tracking**: Current selection index must account for header rows (non-selectable) when navigating up/down.

## Files to Modify

1. **`lince-dashboard/plugin/src/main.rs`**
   - Add `sort_agents()` method on State that groups `self.agents` by `project_dir` and sorts within groups
   - Call `sort_agents()` after agent spawn, kill, and reconcile operations
   - Adjust selection index bounds to skip swimlane header rows

2. **`lince-dashboard/plugin/src/dashboard.rs`**
   - Replace current flat rendering loop with swimlane-aware rendering
   - Add `shorten_path(path: &str) -> String` helper that replaces `$HOME` with `~` and optionally truncates long paths
   - Render swimlane header rows with distinct background color and directory path
   - Show template `group` as a dim suffix on the agent name (e.g., `agent-1 [web-stack]`) instead of its own header
   - Adjust scroll offset calculations to account for extra header rows
   - Update row-count logic used for viewport sizing

3. **`lince-dashboard/plugin/src/types.rs`**
   - No structural changes needed; `project_dir` already exists on `AgentInfo`
   - Consider adding a `display_group() -> String` helper method on `AgentInfo` that returns the swimlane key

## Rendering Layout

```
┌─────────────────────────────────────────────┐
│ 📁 ~/project/lince                          │  ← swimlane header (blue bg)
├─────────────────────────────────────────────┤
│ > agent-1 [web-stack]  RUNNING   1.2K  2m  │  ← selected agent with group label
│   agent-2              INPUT     800   5m  │
├─────────────────────────────────────────────┤
│ 📁 ~/project/other-app                      │  ← swimlane header
├─────────────────────────────────────────────┤
│   agent-3              RUNNING   3.1K  1m  │
└─────────────────────────────────────────────┘
```

## Edge Cases

- All agents in same `project_dir` → single swimlane, no visual difference from current flat list
- Agent with no `project_dir` → group under "(no directory)" swimlane
- Empty swimlane after agent kill → remove header row entirely
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Agents are visually grouped by project_dir with a colored header row showing the directory path
- [x] #2 Directory paths are shortened (~ for $HOME) in swimlane headers
- [x] #3 Agents within each swimlane are sorted by name for stable ordering
- [x] #4 Keyboard navigation (up/down) skips swimlane header rows — only agent rows are selectable
- [x] #5 Template group name is displayed as a dim suffix on the agent name (e.g. agent-1 [web-stack])
- [x] #6 When all agents share the same project_dir, display is visually equivalent to current flat list (single swimlane)
- [x] #7 Scroll offset calculations correctly account for swimlane header rows
- [x] #8 Killing the last agent in a swimlane removes that swimlane header from the display
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented swimlane grouping by project_dir. Added shorten_path() helper (replaces $HOME with ~), sort_agents_by_dir() for stable ordering, swimlane-aware rendering with blue bold headers. Template group shown as dim suffix on agent name. Single-directory case renders flat list (no headers). Virtual-row scrolling accounts for header rows. Navigation operates on agent indices only.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Manual test: spawn agents in 2+ different project_dir values, verify swimlane headers appear and agents are correctly grouped
- [ ] #2 WASM plugin builds successfully: cargo build --target wasm32-wasip1
<!-- DOD:END -->
