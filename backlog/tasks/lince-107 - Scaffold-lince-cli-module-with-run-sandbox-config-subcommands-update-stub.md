---
id: LINCE-107
title: >-
  Scaffold lince-cli module with run / sandbox / config subcommands (update
  stub)
status: To Do
assignee: []
created_date: '2026-05-11 14:59'
labels:
  - enhancement
  - epic-97
milestone: m-14
dependencies: []
references:
  - 'https://github.com/RisorseArtificiali/lince/issues/98'
  - 'https://github.com/RisorseArtificiali/lince/issues/97'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## TLDR

Create the new `lince-cli` module: a Python `argparse`-based CLI installed to `~/.local/bin/lince` with subcommands `run`, `sandbox`, `config` (passthroughs), and `update` (stub for now). Bare `lince` invokes `lince run`. `lince run --floating` flag is in place to replace the future floating alias.

## Why

This is the foundation for the epic. Until `lince` exists as a real binary, none of the other consolidation work can land: passthroughs need a dispatcher, the legacy aliases can't be removed without a replacement, and `lince update` needs a home. The CLI is intentionally minimal in this slice — only scaffolding plus passthroughs that still target the legacy locations on PATH. Later issues swap the targets to the new internal `~/.local/share/lince/bin/` location.

## Implementation plan

1. Create new module folder `/home/maeste/project/lince/lince-cli/` with `lince` (Python, argparse, ~150–200 lines), `install.sh` (copy to `~/.local/bin/lince`, chmod +x), `update.sh` (same as install.sh), `uninstall.sh` (rm the binary), `README.md`.
2. CLI design: `parser.add_subparsers(dest="cmd")`; `p_run --floating` → exec `zellij --layout dashboard-tiled|dashboard-floating`; `p_sandbox` and `p_config` with `add_help=False`, collect extras via `parse_known_args()`, then `os.execvp` to the existing binaries on PATH. `p_update` registered but raises `NotImplementedError("Implemented in #102")`.
3. At top of `main`: if `len(sys.argv)==1`, dispatch to `cmd_run(Namespace(floating=False))`.
4. Passthroughs in this issue exec the **existing** legacy-PATH binaries; path swap to `~/.local/share/lince/bin/` happens in #99.
5. `install.sh` follows `lince-config/install.sh` conventions: Python ≥3.8 check, copy, chmod, summary.
6. Add the module to `quickstart.sh`'s install sequence (after `lince-config`, before final summary).

## Dependencies

- Blocks: #99, #100, #101, #102
- Blocked by: —

## References

- Epic: #97
- Plan: `/home/maeste/.claude/plans/lince-unified-cli-npm.md`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After lince-cli/install.sh, ~/.local/bin/lince exists, is executable, and `lince --help` prints the four subcommands.
- [ ] #2 `lince` with no args launches zellij with the tiled dashboard layout.
- [ ] #3 `lince run --floating` launches zellij with the floating layout.
- [ ] #4 `lince config list` produces identical output to `lince-config list`.
- [ ] #5 `lince sandbox --help` produces identical output to `agent-sandbox --help`.
- [ ] #6 `lince update` exits non-zero with a clear 'not yet implemented, see issue #102' message.
- [ ] #7 `lince-cli/uninstall.sh` removes the binary cleanly.
- [ ] #8 All shell scripts pass `bash -n` and are idempotent (re-running install.sh is a no-op or refresh).
<!-- AC:END -->
