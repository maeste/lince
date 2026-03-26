---
id: LINCE-79
title: Update TOML config files and examples for agent-sandbox paths
status: Done
assignee: []
created_date: '2026-03-25 09:19'
updated_date: '2026-03-25 09:30'
labels:
  - config
  - rename
milestone: m-12
dependencies:
  - LINCE-74
references:
  - sandbox/config.toml.example
  - lince-dashboard/config.toml
  - sandbox/agents-defaults.toml
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update TOML configuration files and examples to reference `agent-sandbox` paths and command name.

**Why**: Config files and examples must use the new name so users see correct paths.

**Implementation plan**:
1. **sandbox/config.toml.example**:
   - Path references: `~/.claude-sandbox/` → `~/.agent-sandbox/`
   - Command references in comments
2. **lince-dashboard/config.toml**:
   - Comment examples referencing `~/.claude-sandbox/`
   - `sandbox_command` default reference in comments
3. **sandbox/agents-defaults.toml**:
   - Comment header referencing `claude-sandbox`
   - If any agent command templates reference `claude-sandbox`
4. Verify: `python3 sandbox/agent-sandbox run -p /tmp/test --dry-run` still works with updated config

**~10 reference changes across 3 files.**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All path references use ~/.agent-sandbox/ in config files
- [x] #2 Config examples use agent-sandbox command name
- [x] #3 agents-defaults.toml header comments reference agent-sandbox
- [x] #4 No remaining claude-sandbox references in any .toml file
<!-- AC:END -->
