---
id: LINCE-108
title: >-
  Move agent-sandbox + lince-config install destination to
  ~/.local/share/lince/bin/
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
  - 'https://github.com/RisorseArtificiali/lince/issues/99'
  - 'https://github.com/RisorseArtificiali/lince/issues/97'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## TLDR

Move `agent-sandbox` and `lince-config` install destinations from `~/.local/bin/` to `~/.local/share/lince/bin/` (off PATH), and update the `lince` CLI's passthroughs to exec from that new location. Add migration that removes any stale copies of the old `~/.local/bin/` binaries.

## Why

`lince` is the only thing meant to be on user PATH. Today both `agent-sandbox` and `lince-config` install there, which leaves the legacy names callable and creates two surfaces for the same functionality. Moving them to a private location keeps the implementations untouched (still callable by `lince sandbox` / `lince config` via `execvp`) while collapsing the user-visible surface to just `lince`. The migration step is what gives existing curl-installed users a smooth upgrade.

## Implementation plan

1. `sandbox/install.sh` + `sandbox/update.sh` — change destination to `~/.local/share/lince/bin/agent-sandbox` (mkdir -p first).
2. `lince-config/install.sh` + `lince-config/update.sh` — same change for `lince-config`.
3. Migration step: if `~/.local/bin/agent-sandbox` or `~/.local/bin/lince-config` exists, `rm -f` after new copy succeeds; print what was removed; only remove the file, not symlink targets.
4. Update `lince-cli/lince`: define `INTERNAL_BIN = Path.home() / ".local/share/lince/bin"` and pass that path to `os.execvp`. Graceful error if the file is missing (pointer to `lince update`).
5. `quickstart.sh` — confirm install order: sandbox + lince-config first, then lince-cli.
6. `sandbox/uninstall.sh` and `lince-config/uninstall.sh` — update paths to match new destination and also try the old `~/.local/bin/` for migrating users.

## Dependencies

- Blocks: #101, #102
- Blocked by: #98

## References

- Epic: #97
- Plan: `/home/maeste/.claude/plans/lince-unified-cli-npm.md` (section "Standalone binary removal")
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After a fresh install, ~/.local/bin/agent-sandbox and ~/.local/bin/lince-config do not exist.
- [ ] #2 ~/.local/share/lince/bin/agent-sandbox and ~/.local/share/lince/bin/lince-config exist, are executable, and run correctly when invoked directly.
- [ ] #3 `lince sandbox --help` and `lince config --help` produce the same output as the direct binaries.
- [ ] #4 Migration test: dummy executables at ~/.local/bin/{agent-sandbox,lince-config} are removed by the install scripts and new copies are present in the internal path.
- [ ] #5 `which agent-sandbox` and `which lince-config` from a regular shell return non-zero / 'not found'.
- [ ] #6 Existing lince-configure skill calls still work once skill update (#101) lands; the path swap alone does not break unrelated code paths.
<!-- AC:END -->
