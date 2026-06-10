---
id: LINCE-110
title: Update lince-configure skill to call `lince config`
status: To Do
assignee: []
created_date: '2026-05-11 14:59'
updated_date: '2026-05-11 15:01'
labels:
  - enhancement
  - epic-97
milestone: m-14
dependencies:
  - LINCE-107
  - LINCE-108
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/101'
  - 'https://github.com/RisorseArtificiali/lince/issues/97'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## TLDR

Rewrite the `lince-configure` Claude skill so every shell-out goes through `lince config <verb>` instead of the now-removed `lince-config <verb>` binary on PATH. The skill at `lince-dashboard/skills/lince-configure/SKILL.md` is ~1008 lines and mentions the legacy command repeatedly.

## Why

The whole point of removing `lince-config` from PATH is to consolidate the user-facing surface. The skill is one of the heaviest consumers of that command — every `get`, `set`, `append`, `list`, `check` invocation goes through it. Until the skill is updated, the skill breaks on a freshly upgraded install. Mechanical but must be done carefully because the file is large.

## Implementation plan

1. Open `lince-dashboard/skills/lince-configure/SKILL.md` and confirm the pattern (most invocations look like `lince-config get …`, `lince-config set … -q`).
2. Find/replace every standalone `lince-config ` (with trailing space, to avoid matching `~/.config/lince-config/`) with `lince config `. Verify no false positives by grepping the file after the replacement — remaining hits should only be in paths or filename-as-documentation.
3. Spot-check the examples (Vertex AI setup, paranoid mode toggle, agent registration) to make sure they still read sensibly.
4. Add a short note near the top of SKILL.md explaining the underlying binary still exists at `~/.local/share/lince/bin/lince-config` for debugging, but the user-facing form is always `lince config <verb>`.
5. Verify companion files in the same skill folder (helpers, example configs) are updated.
6. Search whole repo for other skill files referencing `lince-config`.

## Dependencies

- Blocks: —
- Blocked by: #98, #99

## References

- Epic: #97
- Plan: `/home/maeste/.claude/plans/lince-unified-cli-npm.md` (section "Standalone binary removal", skill subsection)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `grep -rn 'lince-config ' lince-dashboard/skills/lince-configure/` returns zero hits with trailing space (only path-form hits remain).
- [ ] #2 Skill operations work end-to-end on a machine where lince-config is no longer on PATH.
- [ ] #3 `grep -rn 'lince-config ' .` across the repo (excluding path references) returns expected/intentional results only.
- [ ] #4 Skill README/intro text mentions the new command form.
- [ ] #5 No regressions in the skill's natural-language behaviour (semantic spot-check of 3–5 example flows).
<!-- AC:END -->
