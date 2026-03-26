---
id: LINCE-80
title: Update all documentation for agent-sandbox rename
status: Done
assignee: []
created_date: '2026-03-25 09:19'
updated_date: '2026-03-25 09:31'
labels:
  - documentation
  - rename
milestone: m-12
dependencies:
  - LINCE-74
  - LINCE-75
  - LINCE-76
  - LINCE-77
  - LINCE-78
  - LINCE-79
references:
  - sandbox/README.md
  - lince-dashboard/README.md
  - lince-dashboard/MULTI-AGENT-GUIDE.md
  - CLAUDE.md
  - zellij-setup/README.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update all markdown documentation across the project to use `agent-sandbox` instead of `claude-sandbox`. This is the final rename task — depends on all code/config changes being done first.

**Why**: Documentation must reflect the actual command and path names. ~160 references across ~8 markdown files.

**Implementation plan**:
1. **sandbox/README.md** (~95 references):
   - All command examples: `claude-sandbox run` → `agent-sandbox run`, etc.
   - All path examples: `~/.claude-sandbox/` → `~/.agent-sandbox/`
   - Section headers and descriptions
2. **lince-dashboard/README.md** (~27 references):
   - Integration docs, config references, agent defaults location
3. **lince-dashboard/MULTI-AGENT-GUIDE.md** (~8 references):
   - Command examples, config file references
4. **CLAUDE.md** (project root, 2 references):
   - Build verification command
   - Config path in documentation
5. **zellij-setup/README.md** (~9 references):
   - Layout examples with command references
6. Final verification: `grep -r \"claude-sandbox\" --include=\"*.md\"` returns zero results (except historical backlog task titles in `backlog/tasks/`)

**This is the most labor-intensive task (~160 changes) but entirely mechanical — suitable for bulk find-and-replace.**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Zero remaining claude-sandbox references in sandbox/README.md
- [x] #2 Zero remaining claude-sandbox references in lince-dashboard/README.md
- [x] #3 Zero remaining claude-sandbox references in MULTI-AGENT-GUIDE.md
- [x] #4 CLAUDE.md uses agent-sandbox in build command and config path
- [x] #5 zellij-setup/README.md uses agent-sandbox
- [x] #6 grep -r 'claude-sandbox' --include='*.md' returns only backlog task titles (historical)
<!-- AC:END -->
