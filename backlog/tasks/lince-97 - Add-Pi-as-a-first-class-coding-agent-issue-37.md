---
id: LINCE-97
title: 'Add Pi as a first-class coding agent (issue #37)'
status: To Do
assignee: []
created_date: '2026-04-30 22:06'
labels:
  - enhancement
  - agents
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/37'
  - 'https://pi.dev'
  - 'https://github.com/badlogic/pi-mono'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add native support for Pi (https://pi.dev, `@mariozechner/pi-coding-agent`, binary `pi`) as a coding agent in lince. Pi is a minimal terminal coding harness from `badlogic/pi-mono`. Integration includes 3 dashboard variants (unsandboxed, bwrap, nono) and full hook parity with Claude via a Pi extension TS module that emits status events to the existing `lince-status` Zellij pipe. Plan file: `~/.claude/plans/1-ok-2-ok-whimsical-squid.md`.

## Scope
- `sandbox/agents-defaults.toml` — `[agents.pi]` (bwrap config, `home_rw_dirs=[".pi"]`)
- `lince-dashboard/agents-defaults.toml` — `[agents.pi]`, `[agents.pi-bwrap]`, `[agents.pi-nono]` (magenta, `has_native_hooks=true`, shared `lince-status` pipe)
- `lince-dashboard/nono-profiles/lince-pi.json` (modeled on `lince-claude.json`)
- `lince-dashboard/hooks/pi/lince-pi-hook.ts` — Pi extension producing status JSON
- `lince-dashboard/hooks/install-pi-hooks.sh` — copies extension to `~/.pi/agent/extensions/`
- `lince-dashboard/hooks/install-hooks.sh` — dispatcher edit
- Docs: `MULTI-AGENT-GUIDE.md`, `sandbox/README.md`, `sandbox/CHEATSHEET.md`

## Out of scope
- pi-autoresearch (issue #38)
- Bridging Pi's full extension API beyond status events
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Pi is selectable in the dashboard with magenta color and label "PI " in three variants (unsandboxed, bwrap, nono)
- [ ] #2 agent-sandbox run --agent pi launches Pi inside bwrap with ~/.pi mounted rw
- [ ] #3 nono run --profile lince-pi launches Pi with the nono backend
- [ ] #4 Native hooks: dashboard shows status running on agent_start, current_tool on tool_call, idle on agent_end, stopped on session_shutdown
- [ ] #5 lince-dashboard install.sh and update.sh idempotently install/update lince-pi-hook.ts in ~/.pi/agent/extensions/
- [ ] #6 uninstall.sh removes lince-pi-hook.ts
- [ ] #7 Issue #37 acceptance criteria met (default agents list, hooks/lifecycle support, parity with other agents)
- [ ] #8 PR opened against main referencing #37
<!-- AC:END -->
