---
id: LINCE-87
title: Forward transcript_path and session_id from Claude hook to dashboard
status: To Do
assignee: []
created_date: '2026-03-26 10:14'
labels:
  - dashboard
  - relay
  - hooks
  - foundation
milestone: m-12
dependencies: []
references:
  - lince-dashboard/hooks/claude-status-hook.sh
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/agent.rs
  - lince-dashboard/plugin/src/main.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

The Claude Code hook (`claude-status-hook.sh`) receives `session_id` and `transcript_path` in its stdin JSON but does not forward them to the dashboard. Add extraction and forwarding so the dashboard can store the path to the JSONL transcript file per agent.

**Why**: The transcript JSONL file contains structured conversation messages (user prompts, assistant responses). The dashboard needs `transcript_path` to extract messages for the inter-agent relay feature. This is the data bridge between Claude Code and the relay feature.

### Implementation scope

**In `lince-dashboard/hooks/claude-status-hook.sh`**:
1. Extract `session_id` and `transcript_path` via `extract_json_field` (same pattern as `model`, `tool_name`)
2. Do this for ALL hook events where they're present (not just SessionStart), so the dashboard gets updated if session changes
3. Add both fields to the JSON payload — both the jq path and the bash fallback path:
   ```bash
   SESSION_ID=$(extract_json_field "session_id")
   TRANSCRIPT_PATH=$(extract_json_field "transcript_path")
   ```
4. In jq payload builder, add `--arg sid` and `--arg tpath` with conditional inclusion
5. In string-concat fallback, add the same fields

**In `lince-dashboard/plugin/src/types.rs`**:
1. Add to `StatusMessage` struct (both `#[serde(default)]`):
   ```rust
   pub session_id: Option<String>,
   pub transcript_path: Option<String>,
   ```

2. Add to `AgentInfo` struct:
   ```rust
   pub transcript_path: Option<String>,
   ```

**In `lince-dashboard/plugin/src/agent.rs`**:
1. Initialize `transcript_path: None` in `spawn_inner()` AgentInfo constructor

**In `lince-dashboard/plugin/src/main.rs`** (`handle_status_message`):
1. After the existing `model` update block, add:
   ```rust
   if let Some(tp) = msg.transcript_path {
       if !tp.is_empty() {
           agent.transcript_path = Some(tp);
       }
   }
   ```

**Key files**: `hooks/claude-status-hook.sh`, `plugin/src/types.rs`, `plugin/src/agent.rs`, `plugin/src/main.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 Hook extracts session_id and transcript_path from stdin JSON
- [ ] #2 #2 Both fields included in pipe payload (jq path and string-concat fallback)
- [ ] #3 #3 StatusMessage has session_id and transcript_path Optional fields with serde(default)
- [ ] #4 #4 AgentInfo has transcript_path: Option<String> field, initialized to None
- [ ] #5 #5 handle_status_message updates agent.transcript_path when non-empty value arrives
- [ ] #6 #6 transcript_path updates on every hook event (not just SessionStart) for robustness
- [ ] #7 #7 Plugin compiles for wasm32-wasip1 target
<!-- AC:END -->
