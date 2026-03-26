# Contributing to Lince

Thank you for your interest in contributing to the Lince project. This guide covers the different ways you can help.

## Quick ways to contribute

### Validate experimental features

The fastest way to help right now is testing our experimental features. We have a detailed validation guide with step-by-step instructions and checkboxes:

**[sandbox/to-be-validated.md](sandbox/to-be-validated.md)**

Pick any section, run the tests on your system, and report the results. This is especially valuable if you have:
- A different Linux distribution (Fedora, Ubuntu, Arch, Debian, etc.)
- macOS (for nono backend testing)
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
├── voxcode/           Python, uv-managed voice coding assistant
├── voxtts/            Python 3.12, uv-managed TTS
└── backlog/           Task tracking (Backlog.md format)
```

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

## Experimental features

Features marked as **(experimental)** in the documentation are new and have not been extensively validated. They are:

- **Credential proxy isolation** — API keys kept outside sandbox via HTTP proxy
- **Filesystem snapshots and rollback** — rsync-based snapshots with interactive restore
- **Learn mode** — strace-based capability discovery
- **nono backend support** — alternative sandbox using Landlock/Seatbelt
- **nono profile sync** — generate nono profiles from lince config
- **Dashboard nono integration** — launch agents via nono from the TUI dashboard

These features are all backward-compatible and opt-in (except config auto-snapshot, which is on by default but non-breaking).

To promote a feature from experimental to stable, it needs:
1. Validation on at least 2 different environments (see [sandbox/to-be-validated.md](sandbox/to-be-validated.md))
2. No critical bugs reported for 2 weeks
3. Documentation reviewed and accurate

## Questions?

Open an issue. We're happy to help.
