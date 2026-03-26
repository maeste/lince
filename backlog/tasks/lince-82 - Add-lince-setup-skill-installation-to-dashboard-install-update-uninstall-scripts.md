---
id: LINCE-82
title: >-
  Add /lince-setup skill installation to dashboard install/update/uninstall
  scripts
status: Done
assignee: []
created_date: '2026-03-25 09:20'
updated_date: '2026-03-25 09:34'
labels:
  - skill
  - install
milestone: m-12
dependencies:
  - LINCE-81
references:
  - lince-dashboard/install.sh
  - lince-dashboard/update.sh
  - lince-dashboard/uninstall.sh
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update lince-dashboard install scripts to deploy the `/lince-setup` skill to `~/.claude/skills/lince-setup/` and handle update/uninstall.

**Why**: Per project convention, all file copies and system modifications go through install scripts. The skill files must be properly managed.

**Implementation plan**:
1. **install.sh** — add a new step:
   ```bash
   SKILL_SRC=\"$SCRIPT_DIR/skills/lince-setup\"
   SKILL_DST=\"$HOME/.claude/skills/lince-setup\"
   mkdir -p \"$SKILL_DST\"
   cp -r \"$SKILL_SRC/.\" \"$SKILL_DST/\"
   ```
2. **update.sh** — add step to overwrite skill files (safe since skill contains no user state)
3. **uninstall.sh** — add step to remove `~/.claude/skills/lince-setup/`
4. Update summary output to list the skill installation

**~10 lines added across 3 files. Follow existing patterns for hook/wrapper installation steps.**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 install.sh copies skills/lince-setup/ to ~/.claude/skills/lince-setup/
- [x] #2 update.sh overwrites skill files with latest version
- [x] #3 uninstall.sh removes ~/.claude/skills/lince-setup/
- [x] #4 Installation summary lists the skill
- [x] #5 Installation is idempotent
<!-- AC:END -->
