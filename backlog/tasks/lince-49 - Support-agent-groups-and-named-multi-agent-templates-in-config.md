---
id: LINCE-49
title: Support agent groups and named multi-agent templates in config
status: Done
assignee: []
created_date: '2026-03-19 10:40'
updated_date: '2026-03-19 21:51'
labels:
  - dashboard
  - config
  - enhancement
milestone: m-11
dependencies:
  - LINCE-38
  - LINCE-40
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Named templates in config.toml that define sets of agents to spawn together. Agent groups as collapsible dashboard sections.

## Implementation Plan

1. Extend `config.rs` to parse `[templates.<name>]` sections: `agents = [{ name, profile, project }]`
2. Add `group: Option<String>` to `AgentInfo`
3. In `dashboard.rs`: group agents by group name, render collapsible sections (toggle with Enter on group header)
4. Add `t` key to open template selector (list of defined templates)
5. On template selection: spawn all agents defined in template
6. Example config:
   ```toml
   [templates.fullstack]
   agents = [
       { name = "frontend", profile = "anthropic", project = "~/project/frontend" },
       { name = "backend", profile = "vertex", project = "~/project/backend" },
   ]
   ```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Config supports [templates.*] with agent definitions
- [x] #2 t opens template selector
- [x] #3 Template launches all defined agents
- [x] #4 Groups visually separated in dashboard
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added AgentTemplate/TemplateGroup types, [templates.*] config parsing with HashMap→sorted Vec, template selector overlay via 't' key, spawn_agent_from_template() with group assignment, group header rendering in agent table, commented-out example templates in config.toml. Compiles cleanly.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Manual test: define template with 2 agents, launch, verify both appear grouped
<!-- DOD:END -->
