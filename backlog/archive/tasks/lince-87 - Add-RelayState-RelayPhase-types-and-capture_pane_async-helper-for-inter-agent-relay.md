---
id: LINCE-87
title: >-
  Add RelayState/RelayPhase types and capture_pane_async helper for inter-agent
  relay
status: To Do
assignee: []
created_date: '2026-03-25 22:26'
labels:
  - dashboard
  - relay
  - types
  - foundation
milestone: m-12
dependencies: []
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/config.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Add the foundational types and async helper for the inter-agent message relay feature. This feature allows capturing the last N lines from one agent's terminal scrollback and pasting them into another agent's terminal.

**Why**: No way currently exists to share output between agents. Cross-pollination workflows (e.g. "review this analysis from Agent-1") require manual copy-paste across terminal panes.

**Technical constraint**: Zellij-tile 0.42.2 has NO API to read pane scrollback (`get_pane_scrollback` does not exist). The only way to capture pane content is `zellij action dump-screen <file> --full`, which dumps the **focused** pane to a file. This requires briefly focusing the source pane (~150ms).

### Implementation scope

**In `plugin/src/types.rs`** — Add after `NamePromptState`:

```rust
#[derive(Debug, Clone)]
pub enum RelayPhase {
    /// Waiting for user to enter line count (after 'S' press).
    LinePrompt { input: String },
    /// Async dump-screen command in progress.
    Capturing { source_agent_id: String, source_agent_name: String, lines: usize },
    /// Captured text ready for delivery. User must focus a target agent.
    DeliveryPending { source_agent_name: String, captured_text: String, line_count: usize },
}

#[derive(Debug, Clone)]
pub struct RelayState {
    pub phase: RelayPhase,
    pub source_index: usize,
}
```

**In `plugin/src/config.rs`** — Add constant and async helper:

```rust
pub const CMD_CAPTURE_PANE: &str = "capture_pane";

pub fn capture_pane_async(source_agent_id: &str, lines: usize) {
    let script = format!(
        "sleep 0.15; TMPF=$(mktemp /tmp/lince-relay-XXXXXX); \
         zellij action dump-screen \"$TMPF\" --full; \
         tail -n {} \"$TMPF\" | sed 's/\\x1b\\[[0-9;]*[a-zA-Z]//g'; \
         rm -f \"$TMPF\"",
        lines
    );
    run_typed_command_with(
        &["sh", "-c", &script],
        CMD_CAPTURE_PANE,
        &[("source_agent_id", source_agent_id), ("lines", &lines.to_string())],
    );
}
```

The shell script: sleeps 150ms for focus to settle, dumps focused pane to temp file, extracts last N lines stripping ANSI codes, outputs to stdout (returned via `RunCommandResult`), cleans up.

**Key files**: `plugin/src/types.rs`, `plugin/src/config.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 RelayPhase enum exists with variants: LinePrompt, Capturing, DeliveryPending
- [ ] #2 #2 RelayState struct has phase: RelayPhase and source_index: usize fields
- [ ] #3 #3 CMD_CAPTURE_PANE constant exists in config.rs
- [ ] #4 #4 capture_pane_async() runs shell script that dumps focused pane, extracts last N lines, strips ANSI codes
- [ ] #5 #5 capture_pane_async() passes source_agent_id and lines in RunCommandResult context
- [ ] #6 #6 Plugin compiles for wasm32-wasip1 target
<!-- AC:END -->
