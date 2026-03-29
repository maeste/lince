---
id: LINCE-91
title: Update README and MULTI-AGENT-GUIDE with relay feature documentation
status: To Do
assignee: []
created_date: '2026-03-26 10:16'
labels:
  - dashboard
  - relay
  - docs
milestone: m-12
dependencies:
  - LINCE-89
  - LINCE-90
references:
  - lince-dashboard/README.md
  - lince-dashboard/MULTI-AGENT-GUIDE.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Description

Document the inter-agent message relay feature in README.md and MULTI-AGENT-GUIDE.md.

**Why**: Users need to know the feature exists, how to use it, and its limitations (Claude Code only).

### Implementation scope

**In `lince-dashboard/README.md`**:
- Add relay to the feature list: "**Message relay**: Send conversation messages between agents (`s` to relay last message, `S` for N messages)"
- Add relay to the keybindings table: `s` and `S`

**In `lince-dashboard/MULTI-AGENT-GUIDE.md`**:
- Add a "Message Relay" section explaining:
  - How it works (reads Claude Code JSONL transcripts)
  - UX flow: select source → `s`/`S` → select target → `f`/`Enter`
  - Use cases: cross-review, challenging, progress sharing
  - Limitation: Claude Code agents only (requires transcript_path from hooks)
  - Format of relayed text (header/footer, [User]/[Assistant] prefixes)

**Key files**: `lince-dashboard/README.md`, `lince-dashboard/MULTI-AGENT-GUIDE.md`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 #1 README lists relay feature with s/S keybindings
- [ ] #2 #2 MULTI-AGENT-GUIDE has dedicated 'Message Relay' section
- [ ] #3 #3 Documentation explains Claude-only limitation
- [ ] #4 #4 UX flow documented with concrete example
<!-- AC:END -->
