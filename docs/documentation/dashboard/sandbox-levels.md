# Sandbox Levels

LINCE ships three sandbox levels — `paranoid`, `normal`, `permissive` — that let you dial network and filesystem exposure per agent without spawning a separate dashboard entry for every variant. This page documents what each level grants, how to pick one, how to switch backends, and how to ship your own custom level.

## 1. Overview

Sandboxing isolates an AI coding agent from the rest of your machine: the agent sees the project directory and a curated slice of your home, talks to a curated set of network endpoints, and cannot touch your SSH keys, AWS credentials, or arbitrary parts of the filesystem. The goal is to bound the blast radius of a prompt-injected, hallucinating, or simply over-eager agent.

Until recently each combination of "agent type + isolation tightness" required its own entry in `agents-defaults.toml`. The three shipped levels collapse that: every agent type can be launched at any of the three levels through a single `sandbox_level` knob. `paranoid` keeps the agent on a strict diet (one API endpoint, scratch config), `normal` is the default daily-work setting, and `permissive` opens up GitHub and the `gh` CLI for users who need to push branches and open PRs from inside the sandbox.

## 2. The three shipped levels

The table below summarises the differences. Sections after it give the concrete config snippets and behavior for each level.

| Aspect                                  | paranoid (bwrap)              | paranoid (nono)        | normal             | permissive                                              |
|-----------------------------------------|-------------------------------|------------------------|--------------------|---------------------------------------------------------|
| Network (allowed destinations)          | Anthropic API only            | Anthropic API only     | inherited base     | + GitHub + gh CLI domains                               |
| Network isolation enforcement           | kernel (netns) + proxy allowlist | kernel (Landlock + nono policy) | inherited       | proxy allowlist                                         |
| Agent opens raw socket to exfiltrate    | blocked (no route in netns) ✓ | blocked (kernel policy) ✓ | depends on base | blocked for non-allowlisted hosts (proxy)               |
| Filesystem                              | $WORKDIR + scratch ~/.claude  | $WORKDIR + scratch ~/.claude | as today      | + ~/.config/gh, ~/.cache, ~/.ssh/known_hosts            |
| `gh` CLI                                | no                            | no                     | no                 | yes                                                     |
| `docker` / `podman`                     | no                            | no                     | no                 | **no** (out of scope)                                   |
| direct `git push`                       | no                            | no                     | no                 | **no** (use `gh` instead)                               |

### 2.1 Paranoid

**Network.** Only the Anthropic API is reachable, and isolation is **kernel-enforced** on both backends.

- Under bwrap: the sandbox runs in a fresh network namespace (`bwrap --unshare-net`) with only its own loopback. There is no route to anywhere on the host or the internet — a raw TCP connect to `1.1.1.1:443` or a DNS lookup for `attacker.com` fails at the kernel. The host-side credential proxy is reached over a unix domain socket bind-mounted into the sandbox at `/run/lince-proxy.sock`; a small `socat` helper inside the sandbox listens on `127.0.0.1:8118` and forwards each TCP connection to that unix socket. The agent sees `HTTP_PROXY=http://127.0.0.1:8118` and uses TCP localhost as before — no SDK changes are required. On top of the kernel netns isolation, the credential proxy enforces an application-layer allowlist (`allow_domains`, default `["api.anthropic.com"]`); any HTTPS CONNECT or HTTP request to a destination outside the allowlist is rejected with a 403.
- Under nono: kernel-level via Landlock LSM and nono's native network policy; application-level via the same credential proxy mechanism.

The credential proxy injects the API key on the host side in both cases, so the key never enters the sandbox environment. Everything else — DNS for arbitrary hosts, plain HTTPS to other services, even `pip install` from PyPI — fails.

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

**Recommended `gh` token: fine-grained PAT, scoped, non-destructive.** A prompt-injected agent at permissive level can read your `gh` token and act as you on GitHub. The default `gh auth login` token from a CLI device flow inherits broad `repo` scope and can do anything you can do — including delete branches, force-push, change repo settings, and read your other repos. Reduce the blast radius by giving the sandbox its own *fine-grained personal access token*, scoped to only the repository (or repositories) the agent is meant to work on, with permissions chosen so a leaked or coerced token cannot do destructive things.

Create one at <https://github.com/settings/personal-access-tokens/new>:

- **Token name**: pick something recognizable, e.g. `lince-permissive-<repo>` or `lince-sandbox-<project>`.
- **Expiration**: 30–90 days. Rotation is part of the safety budget.
- **Repository access**: select **Only select repositories** and choose the specific repo(s) you want the agent to operate on. Do not pick "All repositories".
- **Account permissions** (left column): leave everything at *No access*. The agent does not need them.
- **Repository permissions** (right column) — these are the sensible defaults for "agent that reads code, opens PRs, manages issues, does not destroy anything":

  | Permission             | Setting        | Why                                                  |
  | ---------------------- | -------------- | ---------------------------------------------------- |
  | Metadata               | Read-only      | Required by all repo operations                      |
  | Contents               | Read and write | Read code, push branches the agent created           |
  | Pull requests          | Read and write | Open PRs, push review comments, update PR body       |
  | Issues                 | Read and write | Read issue context, comment, label                   |
  | Commit statuses        | Read-only      | Lets `gh pr checks` show CI state                    |
  | Actions                | Read-only      | View workflow runs without re-triggering or editing  |
  | Workflows              | **No access**  | Writing workflows from a sandbox is a clear escalation path — agents should not edit `.github/workflows/*` |
  | Administration         | **No access**  | No settings changes, no protections relaxed          |
  | Webhooks               | **No access**  | Webhook control is a back door to repo events        |
  | Secrets / Variables    | **No access**  | Never hand the agent the keys to other tools         |
  | Environments           | **No access**  | Same reasoning as Secrets                            |
  | Codespaces / Pages     | **No access**  | Out of scope for typical agent work                  |

  Anything not listed: leave at *No access*. The above set is enough for the workflows the permissive level was designed for (`gh pr create`, `gh issue comment`, branch push, PR review). Add more only when an agent task actually fails, and revisit this list when GitHub adds new permission scopes.

- **Click "Generate token"** and copy the value somewhere safe (you cannot see it again).

Then point `gh` inside the sandbox at that token instead of your daily one. The cleanest way is to keep the token out of `~/.config/gh/` (which is bind-mounted read-only) and pass it as an environment variable — `GH_TOKEN` is already in the permissive fragment's `[env].passthrough`:

```bash
export GH_TOKEN='github_pat_...'   # from "Generate token"
zd                                  # launch the dashboard normally
```

`gh` inside the sandbox finds `GH_TOKEN` via the passthrough, ignores the broader OAuth token in `~/.config/gh/hosts.yml` (which the agent can still read but `gh` does not prefer when `GH_TOKEN` is set), and operates with the narrow permissions you granted. When you stop the dashboard, `unset GH_TOKEN` if you want the host shell to fall back to your daily token.

If you would rather keep the token in a file: GitHub also accepts the fine-grained PAT through `gh auth login --with-token`, which writes it to `hosts.yml` instead of relying on the env var. Pick whichever fits your habits — the security gain comes from the token's scope, not from how it's stored.

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

**Backend implementation note.** Both backends now achieve kernel-enforced network isolation under paranoid; the implementation paths differ. bwrap paranoid uses `--unshare-net` plus a socat unix-socket bridge to the credential proxy. nono paranoid uses Landlock LSM plus nono's native network policy. From a threat-model standpoint the two are equivalent for paranoid: an agent that opens a raw TCP socket to a non-allowlisted host fails at the kernel level on either backend.

**Prerequisites for paranoid + bwrap.** `socat` must be available on the host's `$PATH` (most distros: install the `socat` package). `install.sh` warns when it is missing. If `unshare_net = true` is resolved at run time and `socat` is not found, `agent-sandbox` errors out with a clear message rather than silently degrading.

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

### Extending the network allowlist with `allow_domains`

`allow_domains` is the user-visible knob that controls which hosts the credential proxy lets through. It appears in the shipped fragments and can be extended by the user without writing a custom level.

- **In paranoid (`unshare_net = true`)**: `allow_domains` is the **strict allowlist**. Any HTTPS CONNECT or HTTP request to a host not in the union of `credential_rules.domains` and `allow_domains` is rejected. The shipped paranoid fragment sets `allow_domains = ["api.anthropic.com"]`.
- **In permissive (`unshare_net = false`)**: `allow_domains` lists the extra hosts the proxy passes through without credential injection. The shipped permissive fragment sets `allow_domains = ["api.github.com", "github.com", "objects.githubusercontent.com"]`.
- **Append-merged, not replaced**: when the user adds `[security] allow_domains = [...]` in `~/.agent-sandbox/config.toml`, the entries are concatenated onto whatever the active fragment ships. Switching from paranoid to permissive (or vice versa) does not silently drop the user's additions, but it does change which fragment's defaults they extend.

### Worked example: paranoid + pypi.org

Suppose you want paranoid for an agent that occasionally needs `pip install` from PyPI. Rather than ship a new fragment file, extend `allow_domains` directly in `~/.agent-sandbox/config.toml`:

```toml
# ~/.agent-sandbox/config.toml
[security]
allow_domains = ["pypi.org", "files.pythonhosted.org"]
```

Then:

```bash
agent-sandbox run --sandbox-level paranoid <command>
```

The resolved config is paranoid + the two extra hosts: kernel netns isolation is unchanged, the proxy allowlist becomes `["api.anthropic.com", "pypi.org", "files.pythonhosted.org"]`, and `pip install` resolves through the proxy. This works because `allow_domains` is append-merged with the paranoid fragment's list, not overwritten.

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

The same mechanism applies to OpenAI Codex, with the keystore account name `openai_api_key`:

- **macOS**: `security add-generic-password -s "nono" -a "openai_api_key" -w "sk-..."`
- **Linux**: `secret-tool store --label "nono openai" service nono account openai_api_key`

## 7. Per-agent specifics

The shipped levels apply across all sandboxed agents, but each agent has quirks worth calling out. The general mechanics are documented above; this section is for the per-agent deltas.

### 7.1 Codex (OpenAI)

Codex's level mappings follow the same shape as Claude's, with a few codex-specific knobs.

| Aspect                                  | paranoid (bwrap)                       | paranoid (nono)              | normal                         | permissive                                              |
|-----------------------------------------|----------------------------------------|------------------------------|--------------------------------|---------------------------------------------------------|
| Network (allowed destinations)          | OpenAI API only                        | OpenAI API only              | inherited base                 | + GitHub + gh CLI domains                               |
| Network isolation enforcement           | kernel (netns) + proxy allowlist       | kernel (Landlock + nono policy) | inherited                  | proxy allowlist                                         |
| `OPENAI_API_KEY` handling               | proxy-injected, **stripped** from env  | proxy-injected, stripped     | passthrough                    | passthrough (codex usually picks token from `~/.codex`) |
| Filesystem (~/.codex)                   | bind-mounted RW (real)                 | per-agent scratch HOME       | as today                       | as today + read on `~/.config/gh`, `~/.cache`, `~/.ssh/known_hosts` |
| `gh` CLI                                | no                                     | no                           | no                             | yes                                                     |
| `disable_inner_sandbox_args`            | preserved (`--sandbox danger-full-access`) | preserved                | preserved                      | preserved                                               |

**Inner-sandbox conflict.** Codex applies its own filesystem sandbox by default. When running under our outer sandbox the two sandboxes fight: codex's seccomp/landlock layer collides with bwrap's PID/mount namespaces, and Landlock-on-Landlock under nono is a non-starter. We disable codex's inner sandbox by passing `--sandbox danger-full-access` on its argv. The wiring lives in two places:

- **bwrap path**: `[agents.codex] disable_inner_sandbox_args = ["--sandbox", "danger-full-access"]` in `agent-sandbox`'s `agents-defaults.toml`. `build_bwrap_cmd` appends these args when `bwrap_conflict = true`.
- **nono path**: hardcoded into the synthesized `inner_command` in `lince-dashboard/plugin/src/agent.rs` (the nono path bypasses agent-sandbox).

Both paths must keep `--sandbox danger-full-access` on the codex argv across all three levels — it is unrelated to network/filesystem isolation; it just turns off the redundant inner layer.

**`OPENAI_API_KEY` handling per level.** Normal and permissive pass `OPENAI_API_KEY` through to the codex process unchanged. Paranoid strips it from the sandbox environment entirely and lets the host-side credential proxy inject the `Authorization: Bearer <key>` header on outbound HTTPS — same model as Claude's `ANTHROPIC_API_KEY` in paranoid. The shipped `sandbox/profiles/codex-paranoid.toml` auto-maps `OPENAI_API_KEY = "$OPENAI_API_KEY"` in `[env.extra]` so the proxy has something to inject without requiring a manual entry in the user's config; if the host env var is unset the rule is silently dropped (same as Claude).

**Scratch ~/.codex on bwrap paranoid.** Unlike Claude (`[claude] use_real_config = false` redirects to `~/.agent-sandbox/claude-config/`), codex has no equivalent host-side scratch mechanism in `agent-sandbox` today. Under bwrap paranoid, the real `~/.codex` is still bind-mounted read-write inside the sandbox. Under nono paranoid, the `lince-dashboard` plugin synthesizes a per-agent bash wrapper that rsyncs `~/.codex` into a scratch HOME under `$XDG_RUNTIME_DIR` and discards it on exit — the agent sees a fresh, isolated config dir. **For threat models that require codex's persistent state to be untouchable, prefer nono paranoid over bwrap paranoid.**

**Common custom levels for codex.** The same `sandbox_level` knob accepts arbitrary suffixes — drop a profile at `~/.config/nono/profiles/lince-codex-<name>.json` (or a TOML fragment under `~/.agent-sandbox/profiles/`) and reference it via `sandbox_level = "<name>"`. Two common patterns:

- **`lince-codex-with-azure`** — adds an `allow_domain` for `<your-resource>.openai.azure.com` so Codex can hit Azure OpenAI. Keep `credentials: ["openai"]` and set `OPENAI_BASE_URL` to your Azure endpoint via `[env.extra]` in the matching agent-sandbox fragment.
- **`lince-codex-with-aws`** — same pattern as the Claude + Bedrock example in §5; replace the `credentials` entry with whatever Bedrock auth scheme your codex setup uses, and grant read access to `~/.aws` for the SDK.

For the master mechanics (file-naming convention, append-merge semantics, choosing a backend), see §4 and §5 above — those rules apply unchanged to codex.

## 8. Future work

The new `sandbox_level` model is what the upcoming wizard ('N' picker) UX changes are built on — the picker becomes a two-axis chooser (agent type x sandbox level) instead of needing a separate `agents.*` entry per variant. Progress is tracked in [GitHub issue #53](https://github.com/RisorseArtificiali/lince/issues/53). [GitHub issue #54](https://github.com/RisorseArtificiali/lince/issues/54) tracks fragment-level `extends` inheritance so custom fragments can declare a parent level explicitly instead of relying on deep-merge order — a smaller, separate scope from the now-completed bwrap paranoid network hardening.

For the manual test plan used to validate this feature, see [`sandbox-levels-testing.md`](./sandbox-levels-testing.md).
