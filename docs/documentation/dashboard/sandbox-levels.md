# Sandbox Levels

LINCE ships three sandbox levels — `paranoid`, `normal`, `permissive` — that let you dial network and filesystem exposure per agent without spawning a separate dashboard entry for every variant. This page documents what each level grants, how to pick one, how to switch backends, and how to ship your own custom level.

## 1. Overview

Sandboxing isolates an AI coding agent from the rest of your machine: the agent sees the project directory and a curated slice of your home, talks to a curated set of network endpoints, and cannot touch your SSH keys, AWS credentials, or arbitrary parts of the filesystem. The goal is to bound the blast radius of a prompt-injected, hallucinating, or simply over-eager agent.

Until recently each combination of "agent type + isolation tightness" required its own entry in `agents-defaults.toml`. The three shipped levels collapse that: every agent type can be launched at any of the three levels through a single `sandbox_level` knob. `paranoid` keeps the agent on a strict diet (one API endpoint, scratch config), `normal` is the default daily-work setting, and `permissive` opens up GitHub and the `gh` CLI for users who need to push branches and open PRs from inside the sandbox.

## 2. The three shipped levels

The table below summarises the differences. Sections after it give the concrete config snippets and behavior for each level.

| Aspect                | paranoid                                | normal                       | permissive                                                                   |
|-----------------------|-----------------------------------------|------------------------------|------------------------------------------------------------------------------|
| Network               | Anthropic API only (proxy)              | inherited base               | + GitHub + gh CLI domains                                                    |
| Filesystem            | $WORKDIR + scratch ~/.claude            | as today                     | + ~/.config/gh, ~/.cache, ~/.ssh/known_hosts                                 |
| `gh` CLI              | no                                      | no                           | yes                                                                          |
| `docker` / `podman`   | no                                      | no                           | **no** (out of scope)                                                        |
| direct `git push`     | no                                      | no                           | **no** (use `gh` instead)                                                    |

### 2.1 Paranoid

**Network.** Only the Anthropic API is reachable. All requests go through nono's credential proxy, which injects the API key on the host side; the key never enters the sandbox environment. Everything else — DNS for arbitrary hosts, plain HTTPS to other services, even `pip install` from PyPI — fails.

nono profile (`~/.config/nono/profiles/lince-claude-paranoid.json`):

```json
{
  "extends": "lince-claude",
  "meta": {
    "name": "lince-claude-paranoid",
    "description": "Claude Code, paranoid sandbox"
  },
  "filesystem": {
    "allow": ["$WORKDIR", "$HOME"],
    "read": []
  },
  "network": {
    "credentials": ["anthropic"]
  }
}
```

agent-sandbox (bwrap) fragment, loaded as `sandbox/profiles/claude-paranoid.toml`:

```toml
[claude]
use_real_config = false

[security]
credential_proxy = true
```

**Filesystem.** The agent gets read/write on `$WORKDIR` (the project directory). `~/.claude` is **not** mounted from your real home — instead `use_real_config = false` (bwrap) and `allow: ["$HOME"]` over a per-agent home (nono) cause the agent to start with a fresh, scratch `~/.claude` that gets `rsync`-seeded from your real config at spawn and discarded when the agent stops. Anything the agent writes to its config dir stays inside that scratch copy.

**Tools.** The agent has its own binary, `git` for local commits, and the standard core utilities. No `gh`, no `curl` to arbitrary hosts, no `docker`, no `podman`.

**What you'd see inside.**

```
$ curl https://example.com
curl: (6) Could not resolve host: example.com

$ gh auth status
gh: command not found  (or: no valid credential found)

$ docker ps
docker: command not found
```

### 2.2 Normal

**Network.** Whatever the base profile of the agent type allows (for `lince-claude` that means the Anthropic API via the credential proxy, plus whatever the `claude-code` upstream nono preset opens up — typically just the Anthropic endpoint). No explicit GitHub allowlist.

nono profile (`~/.config/nono/profiles/lince-claude.json`):

```json
{
  "extends": "claude-code",
  "meta": {
    "name": "lince-claude",
    "description": "LINCE sandbox profile for Claude Code"
  },
  "filesystem": {
    "allow": ["$WORKDIR"],
    "read": ["$HOME/.local/lib"]
  },
  "security": {
    "signal_mode": "allow_same_sandbox"
  }
}
```

For agent-sandbox there is no extra fragment at the `normal` level — it is just the resolved config from `~/.agent-sandbox/config.toml` and the agent's `[claude]` section, with the credential proxy on. This is the level the dashboard ships with by default.

**Filesystem.** Read/write on `$WORKDIR`, read on `$HOME/.local/lib` (so site-packages and similar are visible), the real `~/.claude` mounted read-only or read-write depending on backend defaults. SSH keys, AWS credentials, the rest of `$HOME` — invisible.

**Tools.** Same as paranoid plus whatever the agent's base profile carries. No `gh` unless you opt in.

**What you'd see inside.**

```
$ curl https://example.com         # fails — not in allowlist
$ git commit -am 'wip'              # works (local)
$ gh auth status                    # gh not present
```

### 2.3 Permissive

**Network.** Anthropic API plus an explicit GitHub allowlist: `api.github.com`, `github.com`, `objects.githubusercontent.com`. Enough for `gh auth status`, `gh pr create`, `gh issue list`, and `git fetch`/`git clone` over HTTPS against those hosts.

nono profile (`~/.config/nono/profiles/lince-claude-permissive.json`):

```json
{
  "extends": "lince-claude",
  "meta": {
    "name": "lince-claude-permissive",
    "description": "Claude Code, permissive sandbox"
  },
  "filesystem": {
    "allow": ["$WORKDIR"],
    "read": [
      "$HOME/.config/gh",
      "$HOME/.cache",
      "$HOME/.ssh/known_hosts",
      "$HOME/.local/lib"
    ]
  },
  "network": {
    "network_profile": "developer",
    "credentials": ["anthropic"],
    "allow_domain": [
      "api.github.com",
      "github.com",
      "objects.githubusercontent.com"
    ]
  }
}
```

agent-sandbox (bwrap) fragment, `sandbox/profiles/claude-permissive.toml`:

```toml
[sandbox]
home_ro_dirs = [".config/gh", ".cache", ".ssh/known_hosts"]

[security]
credential_proxy = true
block_git_push = true
```

**Filesystem.** Read/write on `$WORKDIR`. Read-only on `~/.config/gh` (so `gh` finds its token), `~/.cache` (general tool cache reuse), and `~/.ssh/known_hosts` (so SSH-style git remotes don't trip on host-key prompts — the private SSH keys themselves are still hidden).

**Tools.** Adds the `gh` CLI. Direct `git push` is still blocked; the intended push path is `gh pr create` / `gh repo sync`. Docker and Podman are not in scope and are not made reachable — that is a much wider trust boundary and is tracked separately.

**What you'd see inside.**

```
$ gh auth status
github.com — Logged in to github.com as <user> (oauth_token)

$ gh pr create --fill
https://github.com/.../pull/123

$ git push origin HEAD
fatal: remote-helper exited (blocked by sandbox: use `gh` instead)

$ docker ps
docker: command not found
```

## 3. How to choose a level

- **paranoid** when you are running an agent on an untrusted prompt, an unfamiliar repository, or any input you wouldn't paste into a root shell. The agent still does its job for the LLM API path; everything else is denied.
- **normal** for daily work on your own code, where you want the agent to read/write the project, talk to its model, and not much else. This is the right default for most users most of the time.
- **permissive** when you specifically need the agent to inspect or open PRs against GitHub and you accept that `~/.config/gh` is now visible inside the sandbox. The trade-off is real: a prompt-injected agent at this level can read your `gh` token and act as you on GitHub, scoped to whatever permissions that token holds.
- **custom** (see below) when none of the three fit — for example if you need AWS Bedrock, a private Hugging Face mirror, or a corporate proxy.

## 4. Selecting a sandbox backend

The dashboard supports two backends, switched per agent via `sandbox_backend`:

- `sandbox_backend = "bwrap"` — agent-sandbox, Linux only, isolation via Bubblewrap mount/PID namespaces and a host-side credential proxy.
- `sandbox_backend = "nono"` — nono, Linux + macOS, isolation via Landlock (Linux) or Seatbelt (macOS) plus nono's own network policy engine.

The default is per-OS: Linux picks `bwrap` (agent-sandbox), macOS picks `nono`. A Linux user who wants kernel-enforced filesystem isolation via Landlock can override that and pick `nono` explicitly.

**Important asymmetry.** The two backends do not enforce paranoid the same way. Under nono, paranoid is **kernel-enforced**: Landlock restricts the filesystem and nono's native network policy restricts outbound connections. Under bwrap, paranoid is **proxy-enforced**: `use_real_config = false` keeps writes inside the scratch config copy and the credential proxy strips API keys from the sandbox environment, but the bwrap sandbox today does not run with `--unshare-net`. Adding `--unshare-net` would give the sandbox its own loopback and break the host-side credential proxy at `127.0.0.1:PORT`, which is what carries every LLM API call. Tightening this path requires a unix-socket proxy or an in-namespace proxy and is tracked as separate hardening work.

In practice: if you want the strongest available network isolation under paranoid, run on a host where nono is available and set `sandbox_backend = "nono"`.

## 5. Customization

`sandbox_level` is a **free-form profile suffix, not a closed enum**. The three shipped levels are opinionated examples of how to use it. You are expected to ship your own when the defaults don't fit.

The plugin synthesizes the launch command from `(agent_type, sandbox_backend, sandbox_level)` and resolves to a profile file by name. As long as a profile file exists at the expected path, any string works as a level.

File-naming convention:

- **nono**: `~/.config/nono/profiles/lince-<agent>-<level>.json`
- **agent-sandbox**: `~/.agent-sandbox/profiles/<level>.toml` (or in-repo `sandbox/profiles/<level>.toml` for built-ins)

### Worked example: a custom level for AWS Bedrock

Suppose you want a Claude Code agent that can also reach AWS Bedrock. Create `~/.config/nono/profiles/lince-claude-with-aws.json`:

```json
{
  "extends": "lince-claude",
  "meta": {
    "name": "lince-claude-with-aws",
    "description": "claude + AWS Bedrock access"
  },
  "filesystem": {
    "allow": ["$WORKDIR"],
    "read": ["$HOME/.aws"]
  },
  "network": {
    "credentials": ["anthropic"],
    "allow_domain": ["bedrock-runtime.us-east-1.amazonaws.com"]
  }
}
```

What each field grants:

- `extends: "lince-claude"` — start from the LINCE `normal` preset (which itself extends nono's built-in `claude-code` preset). The chain is: `claude-code` (nono built-in) → `lince-claude` (LINCE normal) → `lince-claude-with-aws` (your custom).
- `filesystem.allow: ["$WORKDIR"]` — read/write on the project dir, as before.
- `filesystem.read: ["$HOME/.aws"]` — read-only access to your AWS credentials and config. The agent can use them but cannot modify them.
- `network.credentials: ["anthropic"]` — keeps the Anthropic credential proxy injection on.
- `network.allow_domain: [...]` — opens exactly one extra outbound host: the Bedrock runtime endpoint for `us-east-1`. Other AWS endpoints, and the rest of the internet, remain blocked.

Then in `~/.config/lince-dashboard/config.toml`:

```toml
[agents.claude]
sandbox_level = "with-aws"
```

The next time you spawn a Claude Code agent it will launch with `lince-claude-with-aws` instead of `lince-claude`.

For agent-sandbox (bwrap) users, the equivalent is a TOML fragment at `~/.agent-sandbox/profiles/with-aws.toml` deep-merged into the resolved config (lists appended, scalars overridden); flip the same `sandbox_level = "with-aws"` switch in `agents-defaults.toml` (or in the user `[agents.claude]` override block of `config.toml`) to activate it.

## 6. Keystore setup for paranoid

Paranoid relies on the Anthropic API key being in nono's credential keystore — **not** in `ANTHROPIC_API_KEY` in your environment. The point is that the key never enters the sandbox process tree; nono injects the `Authorization` header on the host side as the request flows through the credential proxy.

Store the key once per machine:

- **macOS** (Keychain):

  ```bash
  security add-generic-password -s "nono" -a "anthropic_api_key" -w "sk-ant-..."
  ```

- **Linux** (libsecret / GNOME Keyring / KWallet):

  ```bash
  secret-tool store --label "nono anthropic" service nono account anthropic_api_key
  ```

  `secret-tool` will prompt for the value on stdin.

For 1Password, Apple Passwords, and other backends, see nono's credential injection docs: https://nono.sh/docs/cli/features/credential-injection.md.

## 7. Future work

The new `sandbox_level` model is what the upcoming wizard ('N' picker) UX changes are built on — the picker becomes a two-axis chooser (agent type x sandbox level) instead of needing a separate `agents.*` entry per variant. Progress is tracked in [GitHub issue #53](https://github.com/RisorseArtificiali/lince/issues/53).

For the manual test plan used to validate this feature, see [`sandbox-levels-testing.md`](./sandbox-levels-testing.md).
