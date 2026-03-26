# agent-sandbox

A lightweight Linux sandbox for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with `--dangerously-skip-permissions` safely. It uses [bubblewrap](https://github.com/containers/bubblewrap) (the same technology behind Flatpak) to restrict what Claude can see and touch on your machine, with near-zero overhead.

## Why

Claude Code's `--dangerously-skip-permissions` flag removes all confirmation prompts, letting Claude execute any bash command, edit any file, and install anything without asking. This is great for productivity but terrifying for your system: a bad prompt, a hallucination, or a prompt injection from malicious code in a repo could wipe your home directory, exfiltrate your SSH keys, push to production, or install a backdoor.

**agent-sandbox** creates a restricted environment where Claude has full autonomy *within* the project you're working on, but physically cannot damage anything else.

## What it blocks

| Attack vector | Protection | How |
|---|---|---|
| **File deletion/modification** | Entire filesystem is read-only except the project dir | `--ro-bind / /` + `--tmpfs $HOME` |
| **SSH key theft** | `~/.ssh` does not exist inside the sandbox | Hidden by tmpfs overlay on `$HOME` |
| **Cloud credential theft** | `~/.aws`, `~/.config/gcloud`, etc. invisible | Hidden by tmpfs overlay on `$HOME` |
| **Git push** | Blocked at three layers | Wrapper script + sanitized `.gitconfig` + no credential helpers |
| **API key exfiltration** | Credential proxy keeps keys outside sandbox | Reverse proxy injects headers; keys never enter sandbox env |
| **Cloud SSRF** | Metadata endpoints blocked | Proxy blocks `169.254.169.254`, `metadata.google.internal`, etc. |
| **Environment variable leaks** | Only whitelisted vars pass through | `--clearenv` + explicit `--setenv` |
| **Process killing/inspection** | Host processes invisible | `--unshare-pid` (PID namespace) |
| **System modification** | Cannot write to `/usr`, `/etc`, `/var` | Read-only root filesystem |
| **DBus/desktop access** | Session bus socket hidden | `--tmpfs /run` |
| **X11/Wayland keylogging** | Display sockets hidden | `--tmpfs /tmp` |
| **Cron/systemd persistence** | Cannot create services or cron jobs | Read-only `/etc`, tmpfs `/run` |

### What it allows

| Capability | Why | How |
|---|---|---|
| **Read/write project directory** | Claude needs to edit your code | `--bind $PWD $PWD` (writable) |
| **Read other projects** | Claude may need to reference sibling repos | `--ro-bind ~/project ~/project` (read-only, configurable) |
| **Network access** | Needed for Anthropic API, pip, npm, git clone | No `--unshare-net` |
| **Build tools** | python, node, cargo, make, gcc, etc. | System dirs read-only + `$HOME` PATH dirs auto-detected |
| **Claude config** | Settings, MCP servers, skills | Isolated copy in `~/.agent-sandbox/claude-config` |
| **Package caches** | `cargo build` can download crates, npm can cache | Persistent writable dirs for registry/cache subdirectories |
| **Filesystem snapshots** | Undo agent damage to project or config dirs | rsync hardlink-based snapshots with interactive restore |

### Security model

The sandbox protects your **host machine from Claude**, not secrets from Claude. Claude still has its own API key (it needs it to function) and can see whatever MCP server credentials are in its config. The threat model is:

1. **Primary**: prompt injection from malicious code in a repository causes Claude to run destructive commands
2. **Secondary**: Claude hallucinating dangerous commands (rm -rf, git push --force, etc.)
3. **Tertiary**: accidental damage from overly broad file operations
4. **API key exfiltration**: with `credential_proxy = true`, API keys never enter the sandbox — the proxy injects them on the host side

The sandbox is **not** a defense against a compromised Claude binary or a kernel-level exploit. For that level of isolation, use a VM.

**Defense layers:**

| Layer | Feature | Default |
|-------|---------|---------|
| Filesystem isolation | Read-only root, tmpfs home | Always on |
| PID namespace | Host processes invisible | On |
| Env var clearing | Only whitelisted vars pass | Always on |
| Git push blocking | Wrapper + sanitized gitconfig | On |
| Credential proxy | API keys never enter sandbox | Opt-in |
| Cloud SSRF blocking | Metadata endpoints blocked by proxy | On (when proxy enabled) |
| Config snapshots | Auto-snapshot before each run | On |
| Project snapshots | Snapshot writable project dir | Opt-in |
| Learn mode | Discover actual access needs | On-demand |

## How it works

agent-sandbox builds a [bubblewrap](https://github.com/containers/bubblewrap) command that sets up a Linux mount namespace. In plain terms, it creates a "view" of the filesystem where:

```
/                           read-only   (entire OS visible but unmodifiable)
├── /tmp                    fresh tmpfs (empty, writable, isolated)
├── /run                    fresh tmpfs (hides DBus, Wayland sockets)
├── /dev                    minimal     (null, zero, random only)
├── /proc                   namespaced  (only sandbox processes visible)
└── /home/you               tmpfs       (entire home hidden)
    ├── .ssh                GONE        (does not exist)
    ├── .aws                GONE
    ├── .gnupg              GONE
    ├── .gitconfig          sanitized   (read-only, no credential helpers)
    ├── .claude/            SANDBOX     (writable isolated copy)
    ├── .local/             read-only   (auto-detected from PATH)
    ├── .cargo/             read-only   (binaries), writable (registry cache)
    ├── project/            read-only   (sibling repos visible)
    │   └── myrepo/         WRITABLE    (your current project)
    └── ...other PATH dirs  read-only   (auto-detected)
```

Environment variables are cleared (`--clearenv`) and only an explicit whitelist is passed through. This prevents leaking `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`, or any other secret that might be in your shell.

Git push is blocked via a wrapper script placed first in `$PATH` that intercepts `git push` and returns an error. Additionally, the `.gitconfig` is sanitized to remove `[credential]` sections, and `push.default` is forced to `nothing`.

## Sandbox Backends (experimental)

> **Status: experimental** — This feature is new and has not been extensively validated. See [to-be-validated.md](to-be-validated.md) for testing instructions.

agent-sandbox supports two isolation backends:

| Backend | Isolation | Platform | Kernel | Dependencies | Default |
|---------|-----------|----------|--------|-------------|---------|
| **agent-sandbox** (bubblewrap) | Linux namespaces | Linux only | 3.8+ | Zero (Python stdlib + bwrap) | Default on Linux |
| **[nono](https://github.com/always-further/nono)** | Landlock LSM / Seatbelt | Linux + macOS | 5.13+ | Rust binary | Required on macOS |

**macOS users**: agent-sandbox is Linux-only. Install nono (`brew install nono`) and set `backend = "nono"` in config.toml. See [nono integration guide](docs/nono-integration.md) for details.

### Switching backends

```toml
# In ~/.agent-sandbox/config.toml
[sandbox]
backend = "auto"          # default: agent-sandbox on Linux, nono on macOS
# backend = "nono"        # force nono
# backend = "agent-sandbox"  # force bwrap
```

### Generating nono profiles

```bash
agent-sandbox nono-sync              # generate profiles for all agents
agent-sandbox nono-sync --dry-run    # preview without writing
agent-sandbox status                 # shows detected backends
```

### Feature comparison

| Feature | agent-sandbox | nono |
|---------|--------------|------|
| Config diff/merge | Yes | No |
| Credential proxy | Yes | Yes (built-in) |
| Filesystem snapshots | Yes | Yes (`nono undo`) |
| Learn mode | Yes (strace) | Yes |
| Per-path granularity | Directory-level | File-level |
| PID isolation | Full namespace | Signal scoping |
| macOS support | No | Yes |

## Requirements

### Linux (agent-sandbox backend)

- **Linux** (any distribution with kernel 3.8+ for user namespaces)
- **Python 3.11+** (for `tomllib` in the standard library)
- **bubblewrap** (`bwrap`)
- **rsync** (for snapshot features; installed by default on all mainstream distros)
- **strace** (for learn mode; installed by default on all mainstream distros)
- **Claude Code** (or another supported AI coding agent)

### macOS (nono backend)

- **Python 3.11+** (for `nono-sync` profile generation)
- **nono** (`brew install nono`)
- **Claude Code** (or another supported AI coding agent)

### Installing bubblewrap

**Fedora / RHEL / CentOS Stream:**
```bash
sudo dnf install bubblewrap
```

**Ubuntu / Debian:**
```bash
sudo apt install bubblewrap
```

**Arch Linux:**
```bash
sudo pacman -S bubblewrap
```

**openSUSE:**
```bash
sudo zypper install bubblewrap
```

Verify it's installed:
```bash
bwrap --version
```

### Installing Claude Code

Follow the [official instructions](https://docs.anthropic.com/en/docs/claude-code/getting-started). Typically:

```bash
npm install -g @anthropic-ai/claude-code
```

Verify:
```bash
claude --version
```

### Installing agent-sandbox

```bash
# Option 1: copy to a directory in your PATH
cp agent-sandbox ~/.local/bin/
chmod +x ~/.local/bin/agent-sandbox

# Option 2: symlink (so updates to the repo are picked up automatically)
ln -s "$(pwd)/agent-sandbox" ~/.local/bin/agent-sandbox
```

Make sure `~/.local/bin` is in your `$PATH`. If it isn't, add this to your `~/.bashrc` or `~/.zshrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Quick start

```bash
# 1. Initialize the sandbox (copies Claude config, sanitizes gitconfig)
agent-sandbox init

# 2. Go to your project
cd ~/project/my-repo

# 3. Run Claude inside the sandbox
agent-sandbox run
```

That's it. Claude starts with `--dangerously-skip-permissions` by default (configurable) and has full autonomy within your project directory, but cannot escape.

Config snapshots are taken automatically before each run (agent config dir is tiny). After the session, run `agent-sandbox snapshot-diff` to see what changed, or `agent-sandbox snapshot-restore` to undo damage.

**Optional hardening:**

```bash
# Enable credential proxy (API keys never enter sandbox)
# Edit ~/.agent-sandbox/config.toml:
#   [security]
#   credential_proxy = true

# Learn what the agent actually needs and tighten the sandbox
agent-sandbox learn --duration 120
agent-sandbox learn --compare
```

## Usage

### Commands

#### `agent-sandbox init`

Sets up the sandbox environment. Run this once, or again with `--force` to reset.

What it does:
- Creates `~/.agent-sandbox/` directory structure
- Copies `~/.claude/` to `~/.agent-sandbox/claude-config/` (isolated copy)
- Generates a sanitized `~/.agent-sandbox/gitconfig` (credential sections stripped)
- Creates a `git` wrapper script that blocks `git push`
- Writes default `~/.agent-sandbox/config.toml`
- Auto-detects `$PATH` entries under `$HOME` and reports them

```bash
agent-sandbox init                # first-time setup
agent-sandbox init --force        # reset everything
agent-sandbox init --real-config  # use real ~/.claude directly (no copy)
```

#### `agent-sandbox run`

Launches an AI coding agent inside the bubblewrap sandbox. Defaults to Claude Code, but supports any agent defined in `agents-defaults.toml` or `[agents.<name>]` config sections.

```bash
agent-sandbox run                        # run Claude Code (default) in current directory
agent-sandbox run -a codex              # run Codex instead of Claude
agent-sandbox run -a gemini             # run Gemini CLI
agent-sandbox run -a opencode           # run OpenCode
agent-sandbox run -p ~/project/foo       # run in a specific project
agent-sandbox run -P zai                 # run with "zai" provider profile
agent-sandbox run --profile mm           # run with "mm" provider profile
agent-sandbox run --safe                 # disable --dangerously-skip-permissions
agent-sandbox run --log                  # enable session transcript logging
agent-sandbox run --dry-run              # print the bwrap command without executing
agent-sandbox run --continue             # --continue passed to the agent automatically
agent-sandbox run --model opus --resume ID  # --model and --resume passed to the agent
agent-sandbox run -- -p                  # -p passed to the agent (--print) via separator
agent-sandbox run -p /tmp --continue     # -p /tmp to sandbox, --continue to the agent
```

**CLI pass-through**: Options not recognized by `agent-sandbox run` are passed directly to the agent. This means you can use agent CLI flags like `--continue`, `--model`, `--resume`, `--print` (long form) without the `--` separator. The `--` separator is still supported for edge cases, e.g. when you need to pass `-p` to the agent (since `-p` is used by agent-sandbox for `--project`).

On launch, it prints a banner showing active protections:
```
agent-sandbox
  profile     zai (Vertex AI via zai project)
  project     /home/you/project/my-repo
  filesystem  read-only root, writable project dir
  network     enabled
  pid isolat. on
  git push    blocked
  env vars    clearenv + whitelist
```

#### `agent-sandbox diff`

Shows a unified diff between your real `~/.claude/` config and the sandbox's isolated copy. Useful to see what Claude changed inside the sandbox (installed MCP servers, modified settings, etc.).

```bash
agent-sandbox diff
```

#### `agent-sandbox merge`

Interactive file-by-file merge of sandbox config changes back to your real `~/.claude/`. For each changed file, you can (a)pply, (s)kip, view (d)iff, or (q)uit.

```bash
agent-sandbox merge
```

This is the safe way to adopt changes Claude made in the sandbox (like installing a new MCP server or skill) into your real environment.

#### `agent-sandbox status`

Shows the current state of the sandbox: config location, file counts, toolchain cache sizes, log count, bwrap version, pending config changes, snapshot info, and credential proxy status.

```bash
agent-sandbox status
```

#### `agent-sandbox proxy-status` (experimental)

Shows the state of the credential proxy: whether it's running, which port, uptime, PID, and configured API domains (keys are never displayed).

```bash
agent-sandbox proxy-status
```

#### `agent-sandbox snapshot` (experimental)

Creates filesystem snapshots of the project directory and/or the agent config directory. Snapshots use rsync with `--link-dest` for hardlink-based deduplication — near-zero disk cost for unchanged files.

```bash
agent-sandbox snapshot                    # snapshot both project and config
agent-sandbox snapshot --config-only      # snapshot config dir only (fast, < 1MB)
agent-sandbox snapshot --project-only     # snapshot project dir only
agent-sandbox snapshot -a codex           # snapshot Codex config dir
```

#### `agent-sandbox snapshot-list` (experimental)

Lists available snapshots grouped by type (project/config) with timestamps and disk usage.

```bash
agent-sandbox snapshot-list               # list all snapshots
agent-sandbox snapshot-list --config      # config snapshots only
agent-sandbox snapshot-list --project     # project snapshots only
```

#### `agent-sandbox snapshot-diff` (experimental)

Compares a snapshot against the current state, or two snapshots against each other. Uses the same comparison engine as `diff`/`merge`.

```bash
agent-sandbox snapshot-diff 20260326T1200  # snapshot vs current state
agent-sandbox snapshot-diff 20260325 20260326  # compare two snapshots (cross-session drift)
agent-sandbox snapshot-diff 2026 --config  # config changes only (prefix matching on timestamps)
```

#### `agent-sandbox snapshot-restore` (experimental)

Interactive restore from a snapshot. Presents each changed file for per-file accept/reject — the same UX as `merge`.

```bash
agent-sandbox snapshot-restore 20260326T1200          # restore project + config
agent-sandbox snapshot-restore 20260326 --config      # restore config only
agent-sandbox snapshot-restore 20260326 --project     # restore project only
```

If restoring a config snapshot and there are unmerged changes in the sandbox config (the `diff` workflow), a warning is printed.

#### `agent-sandbox snapshot-prune` (experimental)

Removes old snapshots beyond the configured maximum count.

```bash
agent-sandbox snapshot-prune              # prune both project and config
agent-sandbox snapshot-prune --config     # prune config snapshots only
agent-sandbox snapshot-prune --all        # prune all types
```

#### `agent-sandbox learn` (experimental)

Runs the agent inside a permissive sandbox with `strace` attached to discover what filesystem paths, network connections, and executables the agent actually uses. Generates a suggested config.toml fragment to tighten or loosen your sandbox.

```bash
agent-sandbox learn                       # learn Claude's access patterns
agent-sandbox learn -a codex              # learn Codex's access patterns
agent-sandbox learn --duration 60         # stop after 60 seconds
agent-sandbox learn --compare             # show over/under-permissive areas vs current config
agent-sandbox learn --apply               # auto-merge suggestions into config.toml
agent-sandbox learn --output report.toml  # save suggestions to a file
```

The report includes:
- Filesystem access categorized by type (project, home config, system, toolchain, temp, unexpected)
- Network connections with reverse DNS resolution
- Executed binaries
- Suggested config changes (add writable dirs, remove unused env vars, etc.)

Requires `strace` to be installed (standard on all Linux distributions).

## Configuration

The config file is searched in order:

1. **`./.agent-sandbox/config.toml`** — project-local (takes priority)
2. **`~/.agent-sandbox/config.toml`** — global fallback

This lets you have project-specific sandbox settings (different profiles, extra writable dirs, etc.) while keeping a global default. If no config is found in either location, the sandbox refuses to start with a clear error.

There is no inline default config — you must always have a real `config.toml` file. Create one with `agent-sandbox init`, or copy an existing one into `.agent-sandbox/` in your project directory.

Here's a reference of every option:

### `[sandbox]`

```toml
[sandbox]
# Extra directories Claude can write to (besides the current project)
extra_rw = []

# Directories Claude can read (but not write)
ro_dirs = ["~/project"]

# Persist build tool caches (cargo registry, npm cache, go modules)
persist_toolchains = true

# Auto-detect PATH entries under $HOME and expose them read-only.
# This makes tools installed in ~/.local/bin, ~/.cargo/bin, ~/.nvm, etc.
# available inside the sandbox without manual configuration.
auto_expose_path = true

# Additional home subdirectories to expose read-only (relative to $HOME).
# .config/gcloud is needed for Vertex AI / Google Cloud authentication.
home_ro_dirs = [".config/gcloud"]
# Other examples: ".rustup", ".nvm", ".pyenv"

# Default provider profile (used when -P is not specified).
# Set to a profile name defined in [profiles.*].
# Leave empty to run without a profile.
default_profile = "zai"
```

### `[claude]`

```toml
[claude]
# Arguments always passed to Claude.
# --dangerously-skip-permissions is the default (the whole point of the sandbox).
# To disable it for a single run, use: agent-sandbox run --safe
default_args = ["--dangerously-skip-permissions"]

# Where the sandbox keeps its isolated copy of Claude's config
config_dir = "~/.agent-sandbox/claude-config"

# Use the real ~/.claude and ~/.claude.json directly (no isolated copy).
# Skips the copy during init and mounts the real dirs in the sandbox.
# Disables diff/merge commands (no separate copy to compare against).
use_real_config = false
```

### `[git]`

```toml
[git]
# Regex patterns for .gitconfig section headers to strip.
# "credential" removes all credential helpers.
# 'url ".*"' removes URL rewrite rules (often used for auth).
strip_sections = ['credential', 'url ".*"']

# Git config values forced in the sanitized gitconfig.
# push.default = nothing means bare `git push` does nothing.
[git.overrides]
"push.default" = "nothing"
```

### `[env]`

```toml
[env]
# Explicit whitelist of host environment variables passed into the sandbox.
# EVERYTHING ELSE IS STRIPPED. This is the main defense against
# leaking AWS_SECRET_ACCESS_KEY, GITHUB_TOKEN, etc.
#
# API keys and provider settings should go in [profiles.*] sections,
# not here. Only terminal/locale vars need passthrough from the host.
passthrough = [
    "TERM",
    "COLORTERM",
    "TERM_PROGRAM",
    "LANG",
    "LC_ALL",
    "EDITOR",
    "VISUAL",
]

# Extra env vars to set inside the sandbox (always applied, regardless of profile)
[env.extra]
# MY_CUSTOM_VAR = "value"
```

### `[logging]`

```toml
[logging]
# Enable transcript logging by default (overridable with --log / --no-log)
enabled = false

# Where log files are stored
dir = "~/.agent-sandbox/logs"
```

When enabled, the session is recorded using the `script` command. Logs are saved as `YYYY-MM-DD_HHMMSS_projectname.log` and contain the full terminal output (including ANSI colors). View them with `cat` (colors preserved) or pipe through `col -b` for plain text.

### `[snapshot]` (experimental)

```toml
[snapshot]
# Auto-snapshot the project directory before each sandbox run.
# Off by default — can be slow for large repos.
auto_project = false

# Auto-snapshot the agent config directory before each sandbox run.
# On by default — config dirs are tiny and corruption is hard to notice.
auto_config = true

# Maximum snapshots to keep per project (oldest pruned automatically)
max_project_snapshots = 3

# Maximum snapshots to keep per agent config
max_config_snapshots = 5

# Directories to exclude from project snapshots
project_exclude = [".git", "node_modules", "target", "__pycache__", ".venv", "build", "dist"]
```

Snapshots are stored in `~/.agent-sandbox/snapshots/` using rsync `--link-dest` for hardlink-based deduplication. Unchanged files share disk blocks with the previous snapshot, so the incremental cost is near-zero.

### `[security]`

```toml
[security]
# PID namespace: Claude can only see its own processes
unshare_pid = true

# New terminal session: prevents escape-sequence attacks on the parent terminal.
# May interfere with Ctrl+C in some terminal emulators. Disabled by default.
new_session = false

# Block git push via a wrapper script
block_git_push = true

# EXPERIMENTAL: Credential proxy — keep API keys outside the sandbox entirely.
# When enabled, a localhost HTTP proxy intercepts API calls and injects
# credentials on the host side — the agent never sees the raw keys.
# API keys must be configured in a [*.profiles.*.env] section.
credential_proxy = false
```

#### `[credential_proxy]` (experimental, optional)

```toml
[credential_proxy]
# Extra hosts to block (cloud metadata endpoints are always blocked)
blocked_hosts = ["169.254.169.254", "metadata.google.internal", "metadata.azure.internal"]
```

### `[profiles.<name>]`

Provider profiles let you put **all credentials in the TOML file** instead of depending on your shell environment. Each profile defines the environment variables needed for a specific Claude provider.

If you have wrapper commands like `zai-claude` and `mm-claude` that set env vars before launching Claude, you can replace them entirely with profiles:

```toml
[sandbox]
# Use "zai" by default when no -P flag is given
default_profile = "zai"

[profiles.zai]
description = "Vertex AI via zai project"
# Optional: override default_args for this profile
# default_args = ["--dangerously-skip-permissions", "--model", "opus"]
[profiles.zai.env]
CLAUDE_CODE_USE_VERTEX = "1"
ANTHROPIC_VERTEX_PROJECT_ID = "my-zai-project"
ANTHROPIC_VERTEX_REGION = "us-east5"

[profiles.mm]
description = "Direct Anthropic API"
[profiles.mm.env]
ANTHROPIC_API_KEY = "sk-ant-api01-..."
```

Usage:
```bash
agent-sandbox run              # uses default_profile ("zai" in example above)
agent-sandbox run -P mm        # override: uses "mm" profile instead
agent-sandbox run -P zai       # explicit: same as default in this case
```

**How it works:**
- `default_profile` in `[sandbox]` sets which profile is used when you just run `agent-sandbox run` without `-P`. All credentials come from the TOML.
- `-P <name>` overrides the default for that invocation.
- Profile env vars are set via bwrap `--setenv` and **do not need to exist in your host shell**. Your shell stays clean.
- The `[env].passthrough` list only needs terminal/locale vars (TERM, LANG, etc.) — no API keys.
- If a profile defines `default_args`, those replace the base `[claude].default_args` for that profile.

**Security note:** Since API keys live in the TOML file, make sure it has appropriate permissions:
```bash
chmod 600 ~/.agent-sandbox/config.toml
```

## Directory layout

After initialization, `~/.agent-sandbox/` contains:

```
~/.agent-sandbox/
├── config.toml             # Sandbox configuration
├── claude-config/          # Isolated copy of ~/.claude (writable by Claude)
│   ├── settings.json
│   ├── CLAUDE.md
│   ├── projects/
│   └── ...
├── gitconfig               # Sanitized .gitconfig (read-only in sandbox)
├── bin/
│   └── git                 # Wrapper that blocks git push
├── toolchains/             # Persistent build caches
│   ├── cargo/
│   │   ├── registry/       # Cargo crate downloads (writable)
│   │   └── git/            # Cargo git checkouts (writable)
│   ├── npm-cache/          # npm download cache (writable)
│   └── go/                 # Go module cache (writable)
├── snapshots/              # Filesystem snapshots (if enabled)
│   ├── projects/           # Project dir snapshots (by project hash)
│   │   └── a1b2c3d4e5f6/
│   │       └── 20260326T120000/
│   └── configs/            # Agent config snapshots (by agent name)
│       └── claude/
│           └── 20260326T120000/
├── proxy.pid               # Credential proxy PID file (when running)
└── logs/                   # Session transcripts (if logging enabled)
    └── 2025-01-15_143022_myrepo.log
```

## How build tools work inside the sandbox

**pip**: Use a virtual environment in your project directory. The venv lives inside the project (writable), so `pip install` works normally:
```bash
python -m venv .venv
source .venv/bin/activate
pip install requests  # works: writes to ./venv/
```

**npm**: `node_modules/` is created in the project directory by default, so `npm install` works out of the box. The npm download cache is redirected to a persistent sandbox directory (`~/.agent-sandbox/toolchains/npm-cache/`).

**cargo**: If you have Rust installed on your system (`~/.cargo/bin/`), the binaries are available read-only. Cargo's registry and git caches are mounted writable from `~/.agent-sandbox/toolchains/cargo/`, so `cargo build` can download dependencies.

**go**: `GOPATH` and `GOMODCACHE` are redirected to `~/.agent-sandbox/toolchains/go/`, so `go build` and `go mod download` work.

**System-installed tools**: Everything in `/usr/bin`, `/usr/local/bin`, etc. is available read-only. If you have tools installed under `$HOME` (via nvm, pyenv, sdkman, etc.), they are auto-detected from your `$PATH` and exposed read-only inside the sandbox.

## Typical workflows

### Daily development

```bash
cd ~/project/my-app
agent-sandbox run
# Claude works freely inside my-app/ but can't touch anything else
```

### Reviewing what Claude changed in config

```bash
# After a sandbox session where Claude installed an MCP server:
agent-sandbox diff
# Shows: +++ sandbox/settings.json has new mcpServers entry

agent-sandbox merge
# [MOD] settings.json
#   apply? (y)es / (n)o / (d)iff / (q)uit: d
#   <shows diff>
#   apply? (y)es / (n)o / (d)iff / (q)uit: y
#   applied.
```

### Switching between providers

```bash
# Define profiles in config.toml (see Configuration section),
# then use -P to select:
agent-sandbox run -P zai           # Vertex AI
agent-sandbox run -P mm            # Direct Anthropic API
agent-sandbox run -P zai --dry-run # inspect the bwrap command for a profile
```

### Using real Claude config (no isolated copy)

By default, `agent-sandbox init` copies `~/.claude/` into the sandbox. This lets you review changes Claude made (via `diff`/`merge`) before applying them to your real config. If you prefer to skip this isolation and let Claude work directly with your real config:

```bash
# Option 1: set during init
agent-sandbox init --real-config

# Option 2: edit config.toml
[claude]
use_real_config = true
```

With `use_real_config = true`:
- `init` skips copying `~/.claude` and `~/.claude.json`
- `run` mounts the real `~/.claude` and `~/.claude.json` writable
- `diff` and `merge` are disabled (no separate copy to compare against)

### Using the credential proxy (experimental)

> **Status: experimental** — See [to-be-validated.md](to-be-validated.md) for testing instructions.

The credential proxy keeps API keys outside the sandbox entirely. Instead of passing `ANTHROPIC_API_KEY` into the sandbox environment, a localhost proxy intercepts API calls and injects the key on the host side. A prompt-injected agent cannot exfiltrate the key because it never exists in the sandbox's memory.

```bash
# 1. Enable in config.toml
[security]
credential_proxy = true

# 2. Put your API key in a profile (it stays on the host)
[claude.profiles.anthropic]
description = "Direct Anthropic API"
[claude.profiles.anthropic.env]
ANTHROPIC_API_KEY = "sk-ant-..."

# 3. Run as usual
agent-sandbox run -P anthropic
# Banner will show: credential_proxy  on (port 54321, domains: api.anthropic.com)
```

The proxy automatically maps these environment variables to API domains:

| Env var | API domain | Header |
|---------|-----------|--------|
| `ANTHROPIC_API_KEY` | `api.anthropic.com` | `x-api-key` |
| `OPENAI_API_KEY` | `api.openai.com` | `Authorization: Bearer` |
| `GOOGLE_API_KEY` | `generativelanguage.googleapis.com` | `x-goog-api-key` |
| `GEMINI_API_KEY` | `generativelanguage.googleapis.com` | `x-goog-api-key` |

Non-API traffic (package managers, git clone, etc.) passes through the proxy via CONNECT tunneling without credential injection.

Cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`, `metadata.azure.internal`) are always blocked to prevent SSRF attacks.

### Snapshots and rollback (experimental)

> **Status: experimental** — See [to-be-validated.md](to-be-validated.md) for testing instructions.

Snapshots protect against agent damage to your project directory or config files. Even if the agent corrupts files inside the writable project dir, you can restore to a known-good state.

```bash
# Take a manual snapshot before a risky session
agent-sandbox snapshot

# After a session, review what changed
agent-sandbox snapshot-diff 20260326

# Restore specific files interactively
agent-sandbox snapshot-restore 20260326
# [MOD] src/main.py
#   restore? (y)es / (n)o / (d)iff / (q)uit: d
#   <shows diff>
#   restore? (y)es / (n)o / (d)iff / (q)uit: y
#   restored.

# Compare what changed between two agent sessions
agent-sandbox snapshot-diff 20260325 20260326

# List and prune old snapshots
agent-sandbox snapshot-list
agent-sandbox snapshot-prune
```

**Auto-snapshots**: By default, config snapshots are taken automatically before each `agent-sandbox run` (the config dir is tiny, so this is free). Project snapshots are opt-in:

```toml
[snapshot]
auto_project = true   # enable project auto-snapshots too
auto_config = true    # default: on
```

**How snapshots relate to diff/merge**: The `diff`/`merge` commands are for reviewing and applying agent changes to your real config (forward flow). Snapshot-restore is for undoing unwanted changes (backward flow). Both use the same comparison engine and interactive UX.

### Learning what the agent needs (experimental)

> **Status: experimental** — See [to-be-validated.md](to-be-validated.md) for testing instructions.

The `learn` command discovers what the agent actually touches, so you can tighten your sandbox configuration.

```bash
# Run Claude for 2 minutes under strace, then analyze
agent-sandbox learn --duration 120

# Output:
# ═══════════════════════════════════════════════════
#  Learn Mode Report — agent: claude
#  Duration: 120s
# ═══════════════════════════════════════════════════
#  📂 Filesystem Access
#  Project files:     89 reads, 23 writes
#  Home config:       12 reads, 3 writes
#  System paths:      45 reads, 0 writes
#  Toolchain caches:   8 reads, 5 writes
#  Unexpected:         0 reads, 0 writes
#
#  🌐 Network Connections
#  api.anthropic.com:443  (12 connections)
#  pypi.org:443           (3 connections)
#
#  📋 Suggested Config Changes
#  ✚ Add writable:  ~/.cache/uv     (uv wrote cache files)
#  ⊖ Remove unused: GOOGLE_API_KEY  (env var never accessed)

# Compare current config vs actual needs
agent-sandbox learn --compare

# Auto-apply suggestions
agent-sandbox learn --apply
```

### Debugging the sandbox

```bash
# See exactly what bwrap command would be executed
agent-sandbox run --dry-run

# Check sandbox state
agent-sandbox status
```

### Logging a session for audit

```bash
agent-sandbox run --log
# After the session:
ls ~/.agent-sandbox/logs/
cat ~/.agent-sandbox/logs/2025-01-15_143022_myrepo.log
```

## Multi-agent support

The sandbox is not limited to Claude Code. It can run any AI coding agent using the `--agent` (`-a`) flag and the `agents-defaults.toml` configuration file.

### Agent configuration

Agent definitions are loaded from three layers (later layers override earlier ones):

1. **`agents-defaults.toml`** — shipped alongside the script (searched in `./.agent-sandbox/`, `~/.agent-sandbox/`, and the script directory)
2. **`[agents.<name>]` in user `config.toml`** — per-user overrides
3. **Hardcoded fallback** — if no config is found, `claude` defaults to the original behavior

Each agent definition specifies the command, default arguments, environment variables, home directory bindings, and bwrap conflict handling:

```toml
[agents.codex]
command = "codex"
default_args = ["--full-auto"]
env = {}
home_ro_dirs = [".codex"]
home_rw_dirs = []
bwrap_conflict = true
disable_inner_sandbox_args = ["--no-sandbox"]
```

### Usage

```bash
agent-sandbox run                  # Run Claude Code (default agent)
agent-sandbox run -a codex         # Run Codex
agent-sandbox run -a gemini        # Run Gemini CLI
agent-sandbox run -a aider         # Run Aider
```

### Handling bwrap conflicts

Some agents (like Codex) use bubblewrap internally. When `bwrap_conflict = true`, the sandbox automatically injects the `disable_inner_sandbox_args` to prevent nested bwrap failures. This is fully config-driven.

### Adding a custom agent

Add an `[agents.<name>]` section to `~/.agent-sandbox/config.toml`:

```toml
[agents.my-agent]
command = "my-agent-binary"
default_args = ["--auto"]
env = {}
home_ro_dirs = [".config/my-agent"]
home_rw_dirs = []
bwrap_conflict = false
disable_inner_sandbox_args = []
```

Then run: `agent-sandbox run -a my-agent`

## Known limitations

1. **Network is open** (without credential proxy): Claude can make outbound HTTP requests. This is necessary for the Anthropic API, package managers, and git clone. A determined prompt injection could exfiltrate project source code via the network. Enable `credential_proxy = true` to at least prevent API key exfiltration and block cloud SSRF endpoints.

2. **Git push bypass**: The `git` wrapper blocks `git push`, but Claude could call `/usr/bin/git push` directly. However, without SSH keys or credential helpers, the push would fail anyway (no authentication available). The wrapper is defense-in-depth.

3. **Not a VM**: bubblewrap uses Linux namespaces, which are a kernel feature. A kernel vulnerability in namespace handling could theoretically allow escape. For higher assurance, run the sandbox inside a VM.

4. **Linux only**: agent-sandbox requires bubblewrap, which depends on Linux kernel namespaces. It does not work on macOS or Windows. macOS users should consider [nono](https://github.com/always-further/nono), which uses macOS Seatbelt for sandboxing and offers similar protections. See `docs/comparison-agent-sandbox-vs-nono.md` for a detailed comparison.

5. **Read-only build tools**: Tools installed under `$HOME` (like `~/.cargo/bin/cargo`) are available read-only. `cargo install new-tool` inside the sandbox will fail. Use system package managers to install new tools, or add specific writable directories via `extra_rw` in config.

6. **MCP server secrets**: If your `~/.claude/settings.json` contains API keys in MCP server environment variables, those are copied to the sandbox. Review `~/.agent-sandbox/claude-config/settings.json` after init and remove any credentials you don't want exposed. With `credential_proxy = true`, API keys configured in profiles are kept outside the sandbox.

7. **Tmpfs home is writable**: The `$HOME` tmpfs overlay is writable (that's how tmpfs works). Claude can create files like `~/temp.txt`, but they are ephemeral and vanish when the sandbox exits. They never touch your real home directory.

8. **Credential proxy and HTTPS**: The credential proxy works by rewriting the agent's `*_BASE_URL` to point to the local proxy, which then forwards with credentials over HTTPS. This means the agent sees `http://localhost:PORT` instead of the real API URL. All major AI SDKs support base URL overrides, so this works transparently. Custom HTTP clients that ignore `*_BASE_URL` env vars will not benefit from the proxy.

9. **Learn mode accuracy**: The `learn` command uses `strace` to trace syscalls, which captures actual I/O but may miss paths that are checked with `access()` or `stat()` without opening. It also runs in a permissive sandbox, so the agent may access paths that would be blocked in the real sandbox. Use the report as guidance, not as an exhaustive specification.

10. **Snapshot disk usage**: While snapshots use hardlinks for deduplication, they still consume disk space for changed files. Monitor usage with `agent-sandbox snapshot-list` and configure `max_project_snapshots` / `max_config_snapshots` to limit growth.

## Troubleshooting

### "bwrap: No permissions to creating new namespace"

Your kernel may have user namespaces disabled. Check:
```bash
sysctl kernel.unprivileged_userns_clone
```
If it returns `0`, enable it:
```bash
sudo sysctl -w kernel.unprivileged_userns_clone=1
# To make permanent:
echo 'kernel.unprivileged_userns_clone=1' | sudo tee /etc/sysctl.d/99-userns.conf
```

### Claude can't find a tool (node, python, etc.)

If the tool is installed under `$HOME` but not in your `$PATH`, add its directory to `home_ro_dirs` in the config:
```toml
[sandbox]
home_ro_dirs = [".nvm", ".pyenv"]
```

### Ctrl+C doesn't work

If you have `new_session = true` in the config, try setting it to `false`. The new-session security feature can interfere with signal propagation in some terminals.

### "API Error: Unable to connect" or DNS failures

On systemd-based distros, `/etc/resolv.conf` is a symlink to `/run/systemd/resolve/stub-resolv.conf`. If the sandbox hides `/run`, DNS breaks. agent-sandbox handles this by only hiding `/run/user/$UID` (DBus/Wayland sockets) instead of all of `/run`. If you still see DNS issues, check:
```bash
# Inside the sandbox:
cat /etc/resolv.conf
# Should show your DNS config, not "No such file"
```

### Using Claude with Vertex AI (Google Cloud)

If you use Claude via Vertex AI, create a profile with the Vertex env vars:
```toml
[sandbox]
home_ro_dirs = [".config/gcloud"]  # Google Cloud ADC credentials
default_profile = "vertex"

[profiles.vertex]
description = "Vertex AI"
[profiles.vertex.env]
CLAUDE_CODE_USE_VERTEX = "1"
ANTHROPIC_VERTEX_PROJECT_ID = "my-gcp-project"
ANTHROPIC_VERTEX_REGION = "us-east5"
```
The `home_ro_dirs` entry for `.config/gcloud` is included in the default config and gives Claude read-only access to your Google Cloud ADC credentials.

Do NOT add `CLAUDECODE` or `CLAUDE_CODE_ENTRYPOINT` to env passthrough or profiles: these are session markers that would trigger "nested session" detection and prevent Claude from starting.

### Claude says "permission denied" writing to a file

The file is outside the writable project directory. Either:
- Move the file into the project, or
- Add the target directory to `extra_rw` in the config:
```toml
[sandbox]
extra_rw = ["/path/to/other/dir"]
```

## License

MIT
