---
id: LINCE-75
title: Update sandbox install/update/uninstall scripts for agent-sandbox rename
status: Done
assignee: []
created_date: '2026-03-25 09:19'
updated_date: '2026-03-25 09:27'
labels:
  - sandbox
  - rename
  - install
milestone: m-12
dependencies:
  - LINCE-74
references:
  - sandbox/install.sh
  - sandbox/update.sh
  - sandbox/uninstall.sh
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update the sandbox module's install/update/uninstall scripts to use the new `agent-sandbox` name for binary installation and config directory setup. Handle migration from the old `claude-sandbox` name.

**Why**: After the executable rename, install scripts must deploy `agent-sandbox` to `~/.local/bin/` and manage `~/.agent-sandbox/` config directory.

**Implementation plan**:
1. **install.sh**: 
   - Change `INSTALL_DST` from `~/.local/bin/claude-sandbox` to `~/.local/bin/agent-sandbox`
   - Change `CONFIG_DIR` from `~/.claude-sandbox` to `~/.agent-sandbox`
   - Add migration step: if `~/.local/bin/claude-sandbox` exists, remove it (print notice)
   - Add migration step: if `~/.claude-sandbox/` exists and `~/.agent-sandbox/` doesn't, copy contents over (print notice)
   - Update all output messages to say `agent-sandbox`
   - Update verification command
2. **update.sh**:
   - Same path changes as install.sh
   - Clean up old binary if present
3. **uninstall.sh**:
   - Remove `~/.local/bin/agent-sandbox`
   - Prompt to remove `~/.agent-sandbox/` directory
   - Also clean up old `~/.local/bin/claude-sandbox` if still present

**~25 reference changes across 3 files.**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Binary installed to ~/.local/bin/agent-sandbox
- [x] #2 Config directory created at ~/.agent-sandbox/
- [x] #3 Old ~/.local/bin/claude-sandbox cleaned up on install with printed notice
- [x] #4 Old ~/.claude-sandbox/ content migrated to ~/.agent-sandbox/ if exists (copy, not move)
- [x] #5 Uninstall removes agent-sandbox binary and optionally ~/.agent-sandbox/
- [x] #6 All output messages reference agent-sandbox not claude-sandbox
- [x] #7 Scripts idempotent and safe to run multiple times
<!-- AC:END -->
