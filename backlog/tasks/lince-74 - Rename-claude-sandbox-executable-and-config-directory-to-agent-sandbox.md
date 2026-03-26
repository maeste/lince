---
id: LINCE-74
title: Rename claude-sandbox executable and config directory to agent-sandbox
status: Done
assignee: []
created_date: '2026-03-25 09:18'
updated_date: '2026-03-25 09:25'
labels:
  - sandbox
  - rename
  - foundation
milestone: m-12
dependencies: []
references:
  - sandbox/claude-sandbox
  - .gitignore
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The sandbox is now agent-agnostic (supports Claude, Codex, Gemini, OpenCode, etc.) but still carries the `claude-sandbox` name. Rename to `agent-sandbox` for consistency with the multi-agent architecture.

**Why**: The name `claude-sandbox` implies Claude-only usage and confuses users who want to sandbox other agents. This is the foundation task — all other rename tasks depend on it.

**Scope**: Rename the script file and update all internal references within the Python script.

**Implementation plan**:
1. `git mv sandbox/claude-sandbox sandbox/agent-sandbox`
2. Update all internal constants:
   - `SANDBOX_DIR = Path.home() / \".claude-sandbox\"` → `Path.home() / \".agent-sandbox\"`
   - All path references to `~/.claude-sandbox/` → `~/.agent-sandbox/`
3. Update argparse program name and description to say `agent-sandbox`
4. Update all `--help` text and docstrings
5. Add backward compatibility: on startup, if `~/.agent-sandbox/` doesn't exist but `~/.claude-sandbox/` does, print a migration notice suggesting the user rename it (do NOT auto-migrate — just warn)
6. Update `.gitignore`: `.claude-sandbox/` → `.agent-sandbox/`
7. Verify: `python3 sandbox/agent-sandbox --help` works, `python3 sandbox/agent-sandbox run -p /tmp/test --dry-run` produces correct output

**Blast radius**: ~30 internal references in the Python script, 1 line in `.gitignore`. This is the smallest self-contained unit — other files depend on this being done first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Script file renamed to sandbox/agent-sandbox
- [x] #2 All internal SANDBOX_DIR and path constants use ~/.agent-sandbox/
- [x] #3 --help output says agent-sandbox, not claude-sandbox
- [x] #4 .gitignore references .agent-sandbox/ instead of .claude-sandbox/
- [x] #5 Backward compat: prints migration notice if ~/.claude-sandbox/ exists but ~/.agent-sandbox/ does not
- [x] #6 python3 sandbox/agent-sandbox run -p /tmp/test --dry-run produces correct bwrap command
- [x] #7 python3 sandbox/agent-sandbox run --agent codex -p /tmp/test --dry-run still works
<!-- AC:END -->
