---
id: LINCE-66
title: 'Per-agent bind mounts, env vars, and config passthrough in sandbox'
status: To Do
assignee: []
created_date: '2026-03-20 17:43'
labels:
  - sandbox
  - config
  - filesystem
milestone: m-12
dependencies:
  - LINCE-57
references:
  - sandbox/claude-sandbox
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Different agents need different config directories and API keys. Add per-agent `home_ro_dirs`, `home_rw_dirs`, and `env` fields to `[agents.<name>]` config sections. Merge priority: profile > agent > base env.

**Why**: Codex needs `~/.codex/` + `OPENAI_API_KEY`, Gemini needs `~/.gemini/` + `GEMINI_API_KEY`, OpenCode needs `~/.config/opencode/`. Without per-agent mounts, agents cannot access their own config files inside bwrap.

**Key file**: `sandbox/claude-sandbox`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each [agents.<name>] section supports home_ro_dirs, home_rw_dirs, env fields
- [ ] #2 Codex config exposes ~/.codex/ read-only and passes OPENAI_API_KEY
- [ ] #3 Gemini config exposes ~/.gemini/ read-only and passes GEMINI_API_KEY
- [ ] #4 OpenCode config exposes ~/.config/opencode/ read-only
- [ ] #5 Merge priority: profile env > agent env > base env
<!-- AC:END -->
