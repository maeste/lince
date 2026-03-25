---
id: LINCE-81
title: Create /lince-setup agentskills.io skill for agent self-registration
status: Done
assignee: []
created_date: '2026-03-25 09:20'
updated_date: '2026-03-25 09:32'
labels:
  - skill
  - agentskills
  - multi-agent
milestone: m-12
dependencies:
  - LINCE-74
references:
  - lince-dashboard/MULTI-AGENT-GUIDE.md
  - sandbox/agents-defaults.toml
documentation:
  - 'https://agentskills.io/specification'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a skill following the agentskills.io specification that helps any AI coding agent self-register its configuration for the lince dashboard and sandbox. The agent knows its own requirements (binary, config dirs, API keys, sandbox behavior); the skill knows the lince config format.

**Why**: Adding a new agent currently requires manually writing ~15 TOML fields in two config files with knowledge of bwrap conflicts, pipe names, wrapper scripts, etc. This skill automates that — the running agent answers questions about itself and the skill generates correct config.

**Skill structure**:
```
lince-dashboard/skills/lince-setup/
├── SKILL.md                          — Main skill (< 500 lines)
├── references/
│   ├── config-schema.md              — Full field reference for both configs
│   └── examples.md                   — Real examples from agents-defaults.toml
└── scripts/
    └── validate-agent.sh             — Validate binary exists, test dry-run
```

**SKILL.md frontmatter** (agentskills.io compliant):
```yaml
name: lince-setup
description: >
  Register a new AI coding agent with the lince-dashboard and agent-sandbox.
  The agent provides its own requirements (binary, config dirs, API keys,
  sandbox behavior) and this skill generates correct TOML configuration.
  Use when adding a new agent type, setting up multi-agent support,
  or \"add agent\", \"register agent\", \"setup agent\", \"configure agent\".
license: MIT
compatibility: Requires lince-dashboard and agent-sandbox installed.
metadata:
  author: lince
  version: \"1.0\"
```

**Skill flow**:
1. **Self-identify**: Agent reports its binary name, config dirs, API keys, default CLI args, bwrap/Docker behavior
2. **Derive config key**: Lowercase, hyphenated from binary name. User confirms.
3. **Check existing**: Read `~/.agent-sandbox/config.toml` for duplicate `[agents.<key>]`. Offer update if exists.
4. **Generate sandbox TOML**: `[agents.<key>]` with command, default_args, env, home_ro_dirs, home_rw_dirs, bwrap_conflict, disable_inner_sandbox_args
5. **Generate dashboard TOML**: `[agents.<key>]` with display_name, short_label, color, sandboxed, has_native_hooks, pane_title_pattern, status_pipe_name
6. **Write config**: Append to config files with user confirmation
7. **Validate**: Run `agent-sandbox run -a <key> -p /tmp/test --dry-run`

**Key design**: Agent knows itself, skill knows lince. Skill provides defaults for lince-specific fields: `has_native_hooks=false`, `status_pipe_name=\"lince-status\"`, `sandboxed=true`, `pane_title_pattern` derived from binary name.

**references/config-schema.md** should document:
- All 7 sandbox config fields with types, defaults, and examples
- All 8 dashboard-specific fields with types, defaults, and examples
- Valid color names (red, green, yellow, blue, magenta, cyan, white)
- Pipe name conventions (claude-status for native, lince-status for wrapper)
- bwrap conflict patterns (which agents typically conflict and why)

**references/examples.md** should contain:
- Complete TOML blocks for claude, codex, gemini, opencode from agents-defaults.toml
- A custom agent example showing all fields

**scripts/validate-agent.sh** should:
- Check binary exists in PATH: `which <binary>`
- Run dry-run: `agent-sandbox run -a <key> -p /tmp/test --dry-run`
- Report success/failure with clear messages
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SKILL.md name field is 'lince-setup' (lowercase, hyphens, matches directory name)
- [x] #2 SKILL.md description is under 1024 chars and includes trigger keywords
- [x] #3 SKILL.md has license, compatibility, and metadata fields per agentskills.io spec
- [x] #4 SKILL.md body is under 500 lines with detailed step-by-step flow
- [x] #5 references/config-schema.md documents all sandbox and dashboard config fields
- [x] #6 references/examples.md contains real TOML examples for all preset agents
- [x] #7 scripts/validate-agent.sh checks binary existence and runs dry-run test
- [x] #8 Skill generates valid TOML that can be parsed by both sandbox and dashboard
- [x] #9 Skill is idempotent — detects existing config and offers update instead of duplicate
<!-- AC:END -->
