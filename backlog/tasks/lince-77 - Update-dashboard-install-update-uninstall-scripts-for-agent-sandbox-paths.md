---
id: LINCE-77
title: Update dashboard install/update/uninstall scripts for agent-sandbox paths
status: Done
assignee: []
created_date: '2026-03-25 09:19'
updated_date: '2026-03-25 09:27'
labels:
  - dashboard
  - rename
  - install
milestone: m-12
dependencies:
  - LINCE-74
references:
  - lince-dashboard/install.sh
  - lince-dashboard/update.sh
  - lince-dashboard/uninstall.sh
  - lince-dashboard/hooks/install-hooks.sh
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update dashboard install scripts to reference `agent-sandbox` paths for agents-defaults.toml deployment, config examples, and output messages.

**Why**: Dashboard scripts deploy `agents-defaults.toml` to the sandbox config directory, which is now `~/.agent-sandbox/`.

**Implementation plan**:
1. **install.sh**:
   - `AGENTS_DEFAULTS_DST` path: `~/.claude-sandbox/agents-defaults.toml` → `~/.agent-sandbox/agents-defaults.toml`
   - `mkdir -p` target: `~/.claude-sandbox` → `~/.agent-sandbox`
   - Summary output messages
2. **update.sh**:
   - Same path changes for agents-defaults copy
   - Config check path
3. **uninstall.sh**:
   - Cleanup path for agents-defaults
4. **hooks/install-hooks.sh**:
   - Configuration instruction text referencing old paths

**~15 reference changes across 4 files.**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Agents-defaults.toml installed to ~/.agent-sandbox/agents-defaults.toml
- [x] #2 All output messages reference agent-sandbox not claude-sandbox
- [x] #3 Config example references use ~/.agent-sandbox/
- [x] #4 Scripts remain idempotent
<!-- AC:END -->
