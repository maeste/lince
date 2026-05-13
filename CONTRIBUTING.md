# Contributing to Lince

Thank you for your interest in contributing to the Lince project. This guide covers the different ways you can help.

## Quick ways to contribute

### Good first issues

These are self-contained tasks that don't require deep knowledge of the codebase:

- **[#19 — Validate macOS support via nono](https://github.com/RisorseArtificiali/lince/issues/19)**: Test the nono sandbox backend on macOS. No code changes needed — just run the test plan in [sandbox/to-be-validated.md](sandbox/to-be-validated.md) section 7 and report results. Requires a Mac with Python 3.11+ and nono installed.

- **[#18 — Gemini CLI login in nono sandbox](https://github.com/RisorseArtificiali/lince/issues/18)**: Gemini CLI asks for login inside the nono sandbox because the D-Bus socket is read-only. A workaround is in place (`GEMINI_FORCE_FILE_STORAGE=true`), but a proper fix would involve granting D-Bus access or upstreaming a nono security group. Good for someone familiar with Linux keyrings/D-Bus.

### Validate on different environments

We have a validation guide with step-by-step test plans:

**[sandbox/to-be-validated.md](sandbox/to-be-validated.md)**

Sections 1–6 are validated on Fedora 43. Section 7 (macOS) needs community validation. Testing on different environments is especially valuable:
- A different Linux distribution (Ubuntu, Arch, Debian, etc.)
- macOS (for nono backend testing — see [#19](https://github.com/RisorseArtificiali/lince/issues/19))
- Older or newer kernel versions
- Non-standard toolchain setups (nvm, pyenv, sdkman, etc.)

To report results: open an issue with the title "Validation: [feature name] on [OS/distro]" and paste the checklist with your results.

### Report bugs

If something doesn't work, open an issue with:
- What you did (command, config, environment)
- What you expected
- What actually happened
- Your environment (OS, kernel version `uname -r`, Python version `python3 --version`)
- For sandbox issues: `agent-sandbox status` output
- For dashboard issues: Zellij version `zellij --version`

### Suggest improvements

Open an issue describing the improvement. For larger changes, discuss the approach before implementing.

## Development setup

### Repository structure

```
lince/
├── sandbox/           Python 3.11+, single-file script, zero deps
├── lince-dashboard/   Rust WASM plugin for Zellij
└── backlog/           Task tracking (Backlog.md format)
```

> **Note**: voxcode and voxtts have been split into their own repositories:
> [github.com/RisorseArtificiali/voxcode](https://github.com/RisorseArtificiali/voxcode) and
> [github.com/RisorseArtificiali/voxtts](https://github.com/RisorseArtificiali/voxtts).

### sandbox (Python)

```bash
# No build step. Verify with:
python3 sandbox/agent-sandbox --help

# Run linting (if ruff is installed):
ruff check sandbox/agent-sandbox
ruff format --check sandbox/agent-sandbox
```

Key rules:
- **Zero external dependencies** — Python stdlib only (Python 3.11+ for `tomllib`)
- **Single file** — everything in `sandbox/agent-sandbox`
- Absolute imports only (never relative)
- Line length: 119 characters
- snake_case for functions/variables, CamelCase for classes

### lince-dashboard (Rust WASM)

```bash
cd lince-dashboard/plugin

# Build (MUST use rustup cargo, not system cargo):
PATH="$HOME/.cargo/bin:$PATH" $HOME/.cargo/bin/cargo build --target wasm32-wasip1

# Never use bare `cargo` — system cargo lacks the wasm target
```

Key rules:
- All file I/O must use `run_command()` (Zellij host calls), not `std::fs` — the WASI sandbox restricts direct filesystem access
- Results arrive asynchronously in `Event::RunCommandResult`
- Use context maps to identify which command result belongs to which operation

### Install scripts

Every module must have `install.sh`, `update.sh`, and `uninstall.sh`:
- All scripts must be **idempotent** (safe to run multiple times)
- All file copies and system modifications go through these scripts — never manual
- The system must be installable by third parties from a clean clone

## Adding a new supported agent

LINCE supports any CLI-based AI coding agent (or shell-like CLI such as
`gh`). To add support for a new one, use the **`lince-add-supported-agent`**
skill installed with the dashboard.

### Quick start

In a Claude Code session inside this repo:

```
/lince-add-supported-agent
```

The skill walks you through a decision tree, generates the right TOML
configuration, and (if applicable) a hook script template you can
customize.

### Tier model

LINCE recognizes three tiers of agent support:

| Tier | Examples | What you get | Maintenance |
|------|----------|--------------|-------------|
| **A — Native hooks** | Claude, Codex, Pi | Full status: Running / INPUT / PERMISSION / Stopped | High (track upstream hook changes) |
| **B — Wrapper-only** | bash, Gemini, OpenCode | Always `-` (Unknown) until exit, then Stopped | Low (TOML only) |
| **C — User-contributed** | Anything else | Same as A or B, but user-side configs only | User maintains it |

When uncertain, **pick Tier B**. You can always promote later by writing
a hook.

Tier A and Tier B agents ship in:
- `lince-dashboard/agents-defaults.toml`
- `sandbox/agents-defaults.toml`
- Hook scripts in `lince-dashboard/hooks/` (Tier A only)

Tier C agents live in user-side configs only:
- `~/.agent-sandbox/config.toml`
- `~/.config/lince-dashboard/config.toml`

### Hook contract

Native hooks (Tier A) emit JSON to a Zellij pipe (default `lince-status`,
configurable via `status_pipe_name`):

```json
{"agent_id": "<id>", "event": "<native_event_name>"}
```

The dashboard's `[agents.<key>.event_map]` translates the native event
name to one of these five canonical states:

- `running` — agent actively working
- `input` — agent waiting for user input
- `permission` — agent asking for approval
- `stopped` — agent process ended
- (`unknown` — never emitted; reserved for "not heard from yet")

Unknown native events (not in `event_map`) → Unknown status with a log
warning (no silent fallback to Running).

For event semantics, hook templates (bash + TS + JS), and the full
contract reference, see
[`lince-dashboard/skills/lince-add-supported-agent/SKILL.md`](lince-dashboard/skills/lince-add-supported-agent/SKILL.md).

### Promoting a Tier C agent to Tier A/B in-tree

We add an agent in-tree (Tier A or B) when:
- It's a widely-used CLI agent benefiting multiple users
- We're willing to take on ongoing maintenance (tracking upstream
  changes)
- It has stable hook semantics (Tier A) or its absence of state is
  acceptable (Tier B)

**Open an issue with the proposal before sending a PR.** The maintainers
will confirm whether the agent is a good fit for in-tree support and
which tier suits it best.

## Code style

- **Python**: ruff defaults, line length 119, absolute imports, type hints where practical
- **Rust**: standard rustfmt, Clippy clean, no `.unwrap()` in library code
- **Shell**: bash, `set -e`, quote variables, use `$()` not backticks
- Be concise in comments — explain "why" not "what"
- No TODO comments in committed code for core functionality

## Pull request guidelines

1. **One feature per PR** — don't bundle unrelated changes
2. **Test before submitting** — run the relevant tests, verify `--help` works
3. **Update documentation** if you add or change user-facing behavior
4. **Update install scripts** if you add new files or dependencies
5. **Don't break backward compatibility** — new features should be opt-in
6. **Keep the PR focused** — a small PR that does one thing well is better than a large one

### Commit messages

- Use present tense ("Add feature" not "Added feature")
- First line: concise summary under 72 characters
- Body (if needed): explain why, not what

### PR description

- Summary of what changed and why
- How to test it
- Any backward compatibility considerations

## Feature status

### Validated (Linux)

These features have been validated on Linux (Fedora 43, kernel 6.18) and are considered stable:

- **Credential proxy isolation** — API keys kept outside sandbox via HTTP proxy
- **Filesystem snapshots and rollback** — rsync-based snapshots with interactive restore
- **Learn mode** — strace-based capability discovery
- **nono backend support (Linux)** — alternative sandbox using Landlock LSM
- **nono profile sync** — generate nono profiles from lince config
- **Dashboard nono integration** — launch agents via nono from the TUI dashboard

### Experimental

- **macOS support via nono** — nono's Seatbelt backend on macOS has not been validated ([#19](https://github.com/RisorseArtificiali/lince/issues/19))

### Known issues

- **Gemini CLI login in nono** — D-Bus socket restrictions cause Gemini to ask for login ([#18](https://github.com/RisorseArtificiali/lince/issues/18)). Workaround applied in `agents-defaults.toml`.

To promote a feature from experimental to stable, it needs:
1. Validation on at least 2 different environments (see [sandbox/to-be-validated.md](sandbox/to-be-validated.md))
2. No critical bugs reported for 2 weeks
3. Documentation reviewed and accurate

## Questions?

Open an issue. We're happy to help.
