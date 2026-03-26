---
id: LINCE-88
title: >-
  Add RelayState types and transcript extraction helper for structured message
  relay
status: To Do
assignee: []
created_date: '2026-03-26 10:15'
labels:
  - dashboard
  - relay
  - types
  - foundation
milestone: m-12
dependencies:
  - LINCE-87
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/config.rs
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Add the foundational types for the relay state machine and an async helper that extracts the last N conversation messages from a Claude Code JSONL transcript file.

**Why**: The relay feature needs a state machine (prompt → extract → deliver) and a way to read structured messages from the transcript. Python3 is used for extraction because JSONL with nested content arrays is awkward in jq but trivial in Python (and Python3 is guaranteed present — Claude Code requires it).

### Implementation scope

**In `plugin/src/types.rs`** — Add after `NamePromptState`:

```rust
#[derive(Debug, Clone)]
pub enum RelayPhase {
    /// User pressed S, entering message count (1-9).
    MessagePrompt { input: String },
    /// Async extraction from transcript in progress.
    Extracting {
        source_agent_id: String,
        source_agent_name: String,
        message_count: usize,
    },
    /// Extracted messages ready for delivery to target.
    DeliveryPending {
        source_agent_name: String,
        captured_text: String,
        message_count: usize,
    },
}

#[derive(Debug, Clone)]
pub struct RelayState {
    pub phase: RelayPhase,
    pub source_index: usize,
}
```

**In `plugin/src/config.rs`** — Add constant and async helper:

```rust
pub const CMD_EXTRACT_TRANSCRIPT: &str = "extract_transcript";

pub fn extract_transcript_async(
    source_agent_id: &str,
    transcript_path: &str,
    message_count: usize,
) {
    // Python3 script: read JSONL, filter user/assistant text messages, format last N
    let script = format!(
        r#"python3 -c "
import json, sys
msgs = []
for line in open('{path}'):
    line = line.strip()
    if not line: continue
    try: d = json.loads(line)
    except: continue
    t = d.get('type','')
    if t not in ('user','assistant'): continue
    content = d.get('message',{{}}).get('content',[])
    texts = [c['text'].strip() for c in content if isinstance(c,dict) and c.get('type')=='text' and c.get('text','').strip()]
    if texts:
        role = 'User' if t == 'user' else 'Assistant'
        msgs.append('[' + role + ']: ' + ' '.join(texts))
for m in msgs[-{count}:]:
    print(m)
    print()
" 2>/dev/null || echo '[error] python3 extraction failed'"#,
        path = shell_escape(transcript_path),
        count = message_count,
    );
    run_typed_command_with(
        &["sh", "-c", &script],
        CMD_EXTRACT_TRANSCRIPT,
        &[
            ("source_agent_id", source_agent_id),
            ("message_count", &message_count.to_string()),
        ],
    );
}
```

Reuses existing `shell_escape()` and `run_typed_command_with()` from config.rs.

**Key files**: `plugin/src/types.rs`, `plugin/src/config.rs`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 RelayPhase enum has variants: MessagePrompt, Extracting, DeliveryPending
- [ ] #2 #2 RelayState struct has phase and source_index fields
- [ ] #3 #3 CMD_EXTRACT_TRANSCRIPT constant exists in config.rs
- [ ] #4 #4 extract_transcript_async() runs python3 script that reads JSONL, filters user/assistant text, outputs last N formatted messages
- [ ] #5 #5 Passes source_agent_id and message_count in RunCommandResult context via run_typed_command_with
- [ ] #6 #6 Python script falls back gracefully on error (prints error marker)
- [ ] #7 #7 Plugin compiles for wasm32-wasip1
<!-- AC:END -->
