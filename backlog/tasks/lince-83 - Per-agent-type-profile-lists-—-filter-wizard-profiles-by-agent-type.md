---
id: LINCE-83
title: Per-agent-type profile lists — filter wizard profiles by agent type
status: Done
assignee: []
created_date: '2026-03-25 13:49'
updated_date: '2026-03-25 14:07'
labels:
  - dashboard
  - wizard
  - profiles
  - UX
milestone: m-12
dependencies:
  - LINCE-56
  - LINCE-63
references:
  - lince-dashboard/plugin/src/types.rs
  - lince-dashboard/plugin/src/main.rs
  - lince-dashboard/plugin/src/dashboard.rs
  - lince-dashboard/plugin/src/config.rs
  - lince-dashboard/agents-defaults.toml
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Problem**: When creating a new agent via the "N" wizard, all sandbox profiles (discovered from `~/.agent-sandbox/config.toml`) are shown regardless of agent type. Profiles like "anthropic" or "vertex" only make sense for Claude agents — they are meaningless for Codex, Gemini, or OpenCode.

**Solution**: Add a `profiles` field to `AgentTypeConfig` so each agent type declares which profiles apply to it.

**Implementation**:

1. **Add `profiles` field to `AgentTypeConfig`** (`types.rs`):
   - `profiles: Option<Vec<String>>` — list of profile names valid for this agent type
   - `None` or empty = skip the profile wizard step for this agent type

2. **Update `agents-defaults.toml`** (dashboard):
   - `claude`: `profiles = ["anthropic", "vertex", ...]` (or `profiles = "__auto__"` to inherit from discovered profiles)
   - `claude-unsandboxed`: `profiles = []` (no profiles)
   - `codex`, `gemini`, `opencode`: `profiles = []` (no profiles)

3. **Update wizard flow** (`main.rs` / `dashboard.rs`):
   - When wizard initializes, resolve the effective profile list for the selected agent type
   - If the agent type has no profiles (empty or None), skip the profile step entirely
   - If the agent type has profiles, show only those profiles (intersected with discovered profiles)

4. **Handle agent type switching in wizard**:
   - When user changes agent type in the wizard, re-evaluate whether the profile step should be shown
   - Reset profile_index if the new agent type has different profiles

5. **Config merge logic** (`config.rs`):
   - User overrides in `config.toml` `[agents.<name>]` can set `profiles = [...]` to override defaults
   - Special value like `"__discover__"` or omitting the field could mean "use all discovered profiles"

**Design decision**: The `profiles` field lives on the agent type config, NOT on the global dashboard config. This keeps the association explicit and per-agent-type.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Wizard only shows profiles relevant to the selected agent type
- [x] #2 Agent types with no profiles skip the profile step entirely
- [x] #3 Claude agent type shows discovered profiles from ~/.agent-sandbox/config.toml
- [x] #4 Codex, Gemini, OpenCode agent types skip the profile step
- [x] #5 User can override per-agent profiles in config.toml [agents.<name>]
- [x] #6 Changing agent type in wizard updates the profile step visibility
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `profiles` field to `AgentTypeConfig` with `__discover__` sentinel support. Wizard now resolves profiles per agent type: claude gets all discovered profiles, other agents skip the profile step. Profiles re-resolve on agent type change in the wizard.
<!-- SECTION:FINAL_SUMMARY:END -->
