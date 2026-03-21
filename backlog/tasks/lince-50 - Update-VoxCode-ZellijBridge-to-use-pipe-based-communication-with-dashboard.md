---
id: LINCE-50
title: Update VoxCode ZellijBridge to use pipe-based communication with dashboard
status: Done
assignee: []
created_date: '2026-03-19 10:41'
updated_date: '2026-03-19 21:51'
labels:
  - voxcode
  - dashboard
  - integration
milestone: m-11
dependencies:
  - LINCE-43
references:
  - voxcode/src/voxcode/zellij_bridge.py
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add `use_pipe` mode to VoxCode's ZellijBridge, sending transcribed text via `zellij pipe` instead of focus+write-chars. This enables the dashboard plugin to route text to the correct agent.

## Implementation Plan

1. In `voxcode/src/voxcode/zellij_bridge.py`: add `use_pipe: bool` config field (default False)
2. When `use_pipe = True`: replace focus-switch + write-chars with `subprocess.run(["zellij", "pipe", "--name", "voxcode-text", "--payload", text])`
3. Add `[zellij] use_pipe = false` to voxcode config.toml (backward compatible default)
4. Update `voxcode/README.md` with pipe mode documentation and dashboard integration instructions
5. Keep existing direct mode as default for non-dashboard workflows
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 use_pipe config option exists in voxcode [zellij] section
- [x] #2 When enabled, text sent via zellij pipe instead of write-chars
- [x] #3 When disabled, existing behavior preserved
- [ ] #4 End-to-end: VoxCode pipe -> dashboard -> agent pane
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added use_pipe parameter to ZellijBridge (default False). When enabled, send_text() uses `zellij pipe --name voxcode-text --payload TEXT` instead of focus+write-chars. Wired through ZellijConfig dataclass and create_bridge factory. Pipe name matches dashboard's expected voxcode-text pipe handler. Existing behavior fully preserved when use_pipe=False.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Both pipe and legacy modes tested
- [x] #2 No regression in existing non-dashboard workflows
<!-- DOD:END -->
