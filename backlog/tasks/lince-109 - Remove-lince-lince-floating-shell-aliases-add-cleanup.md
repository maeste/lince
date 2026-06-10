---
id: LINCE-109
title: Remove lince / lince-floating shell aliases; add cleanup
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
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/100'
  - 'https://github.com/RisorseArtificiali/lince/issues/97'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## TLDR

Stop writing `alias lince=...` and `alias lince-floating=...` into `~/.bashrc` / `~/.zshrc` from the dashboard installer, and add a one-time cleanup that strips those alias lines on upgrade. Keep unrelated zellij shortcuts (`zd`, `z`, `zn`).

## Why

Once `~/.local/bin/lince` exists as a real binary, the shell aliases either shadow it (breaking subcommands like `lince config`) or are simply redundant. They have to go. Existing installs already have the alias lines in their rc files, so the upgrade path needs to strip them deterministically — easiest done via the marker-comment block the dashboard installer writes around its alias edits.

## Implementation plan

1. `lince-dashboard/install.sh` (~lines 280–290 today, verify): remove the lines that write `alias lince=...` and `alias lince-floating=...`. Keep the rest of the alias block (`zd`, `z`, `zn`).
2. `lince-dashboard/update.sh`: same change.
3. Identify the marker-comment block the dashboard install.sh wraps around its rc-file edits (typically `# >>> lince-dashboard >>>` / `# <<< lince-dashboard <<<` or similar). Confirm in current source.
4. Cleanup step in install.sh and update.sh: before re-writing the (now-smaller) alias block, scan `~/.bashrc` and `~/.zshrc` for legacy `alias lince=...` / `alias lince-floating=...` lines inside the marker block and remove them via `sed -i` with patterns scoped between markers.
5. Test idempotency: running the cleanup twice should leave the rc file in the same state.
6. `lince-cli/install.sh` should also run the cleanup defensively.

## Dependencies

- Blocks: —
- Blocked by: #98

## References

- Epic: #97
- Plan: `/home/maeste/.claude/plans/lince-unified-cli-npm.md` (section "Shell-alias cleanup")
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After running lince-dashboard/install.sh (or update.sh) on a clean rc file, no `alias lince=` line is present.
- [ ] #2 After running lince-dashboard/install.sh on an rc file that contains the legacy `alias lince=...` line, the line is removed and the rest of the file (including zd, z, zn aliases) is untouched.
- [ ] #3 Running install.sh twice in a row produces identical rc files (idempotent).
- [ ] #4 `command -v lince` resolves to ~/.local/bin/lince (real file), not an alias.
- [ ] #5 `lince run --floating` works (replaces what `lince-floating` did).
- [ ] #6 An rc file with custom user content outside the marker block is preserved exactly.
<!-- AC:END -->
