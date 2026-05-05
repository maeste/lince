# Sandbox Levels — Manual Test Plan

See [`sandbox-levels.md`](./sandbox-levels.md) for the design and configuration reference.

This is a pre-merge checklist for the LINCE three-level sandbox feature (`paranoid` / `normal` / `permissive`) on the Claude Code agent prototype. Each cell of `level x backend` has its own block of commands. Run the cells that apply to your platform, then walk the regression checklist, then sign off at the bottom.

The Claude prototype is the only agent type wired to `sandbox_level` in this iteration. Other agent types (codex, gemini, opencode, pi) are explicitly part of the regression checklist below — they must keep working unchanged.

## 1. Prerequisites

- LINCE installed: `zd` alias works, dashboard launches via `zellij --layout dashboard`.
- agent-sandbox (`bwrap` backend) installed and on `$PATH`. Verify:
  ```bash
  agent-sandbox --version
  ```
- `socat` installed on the host (required for paranoid + bwrap; the bwrap netns reaches the credential proxy via a unix-socket bridge driven by `socat`). Verify:
  ```bash
  socat -V | head -n 1
  ```
  If missing: `sudo dnf install socat` (Fedora) or `sudo apt install socat` (Debian/Ubuntu).
- nono installed and on `$PATH`. Verify:
  ```bash
  nono --version
  ```
- Anthropic API key exported in the env (used by `normal` and `permissive`):
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  ```
- Anthropic API key stored in the nono keystore (used by `paranoid` on the nono backend). Run once per machine:
  - Linux (libsecret / GNOME Keyring / KWallet):
    ```bash
    secret-tool store --label "nono anthropic" service nono account anthropic_api_key
    ```
  - macOS (Keychain):
    ```bash
    security add-generic-password -s "nono" -a "anthropic_api_key" -w "sk-ant-..."
    ```
- A clean test project directory:
  ```bash
  mkdir -p /tmp/lince-test && cd /tmp/lince-test && git init
  ```
- A GitHub token reachable from `~/.config/gh` (`gh auth login` once on the host) — required only for the `permissive` cells.

## 2. Test matrix

| Level x Backend | bwrap (linux)    | nono (linux)     | nono (macOS)              |
|-----------------|------------------|------------------|---------------------------|
| paranoid        | yes              | yes              | yes (if mac available)    |
| normal          | smoke regression | smoke regression | smoke regression          |
| permissive      | yes              | yes              | yes (if mac available)    |

`bwrap` on macOS is **not applicable** — agent-sandbox is Linux-only. Skip those cells on macOS hosts.

## 3. Test cells

### 3.1 Cell: paranoid x bwrap (linux)

#### Setup
1. In `~/.config/lince-dashboard/config.toml`, set or override:
   ```toml
   [agents.claude]
   sandbox_level = "paranoid"
   sandbox_backend = "bwrap"
   ```
2. Restart Zellij so the plugin reloads the config.
3. Spawn a Claude agent: press `n` in the dashboard, accept defaults.

#### Inside the sandbox (run in claude's bash pane)
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://attacker.com 2>&1`
  - Expected: kernel-level connection failure (e.g. `Could not resolve host: attacker.com` or `Network is unreachable`), **not** a 403 from a proxy. This verifies the bwrap netns isolation: the sandbox has no route to anywhere except its own loopback.
- Command: `python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('1.1.1.1', 443))"`
  - Expected: `OSError` (typically `Network is unreachable` or `No route to host`). The fresh netns has no route to non-loopback addresses, so even raw-socket bypasses of `HTTP_PROXY` fail.
- Command: `printenv | grep -E "(ANTHROPIC|OPENAI|GEMINI)_API_KEY"`
  - Expected: empty output. The credential proxy strips API keys from the sandbox environment.
- Command: send a chat message that triggers a real Anthropic API call.
  - Expected: normal response. The agent reaches the credential proxy via `HTTP_PROXY=http://127.0.0.1:8118`, which the in-sandbox `socat` helper bridges to the host-side proxy over the unix socket at `/run/lince-proxy.sock`.
- Command: `ls -la ~/.claude/`
  - Expected: a scratch copy of claude settings, NOT the real one. No personal history files outside what was rsync-seeded at spawn.
- Command: `touch ~/.claude/MUTATED_BY_AGENT && ls ~/.claude/MUTATED_BY_AGENT`
  - Expected: file exists inside the scratch copy.

#### Outside the sandbox (host shell, while the agent is still running)
- Command: `ls ~/.claude/MUTATED_BY_AGENT`
  - Expected: `No such file or directory`. The real config is untouched.
- Command: `pgrep -af socat`
  - Expected: at least one `socat` process per running paranoid+bwrap agent, listening on the per-agent unix socket and bridging to `127.0.0.1:8118` inside the netns.

#### After agent stop
- Command: `ls "$XDG_RUNTIME_DIR"/lince-* 2>/dev/null`
  - Expected: no output. Cleanup ran and the scratch copy is gone.
- Command: `pgrep -af socat | grep lince-proxy`
  - Expected: no output. The bridge `socat` was torn down with the agent.

### 3.2 Cell: paranoid x nono (linux)

#### Setup
1. In `~/.config/lince-dashboard/config.toml`:
   ```toml
   [agents.claude]
   sandbox_level = "paranoid"
   sandbox_backend = "nono"
   ```
2. Restart Zellij.
3. Spawn a Claude agent.

#### Inside the sandbox
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://example.com`
  - Expected: connection failure. Under nono this is kernel-enforced via Landlock + nono's network policy.
- Command: send a chat message that triggers a real Anthropic API call.
  - Expected: normal response (credential proxy injects key).
- Command: `ls -la ~/.claude/`
  - Expected: scratch copy via the per-agent home, not the real `~/.claude`.
- Command: `touch ~/.claude/MUTATED_BY_AGENT && ls ~/.claude/MUTATED_BY_AGENT`
  - Expected: file present inside the scratch copy.

#### Outside the sandbox
- Command: `ls ~/.claude/MUTATED_BY_AGENT`
  - Expected: `No such file or directory`.

#### After agent stop
- Command: `ls "$XDG_RUNTIME_DIR"/lince-* 2>/dev/null`
  - Expected: no output.

### 3.3 Cell: paranoid x nono (macOS)

Run only if a macOS host is available.

#### Setup
1. Same config block as 3.2 in `~/.config/lince-dashboard/config.toml`.
2. Restart Zellij.
3. Spawn a Claude agent.

#### Inside the sandbox
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://example.com`
  - Expected: connection failure. macOS uses Seatbelt for filesystem isolation plus nono's network policy.
- Command: send a chat message that triggers a real Anthropic API call.
  - Expected: normal response.
- Command: `ls -la ~/.claude/`
  - Expected: scratch copy, not the real one.
- Command: `touch ~/.claude/MUTATED_BY_AGENT && ls ~/.claude/MUTATED_BY_AGENT`
  - Expected: file inside scratch.

#### Outside the sandbox
- Command: `ls ~/.claude/MUTATED_BY_AGENT`
  - Expected: `No such file or directory`.

#### After agent stop
- Command: `ls /tmp/lince-* 2>/dev/null` (macOS does not export `XDG_RUNTIME_DIR` by default)
  - Expected: no output.

### 3.4 Cell: normal x bwrap (linux) — smoke regression

#### Setup
1. In `~/.config/lince-dashboard/config.toml`:
   ```toml
   [agents.claude]
   sandbox_level = "normal"
   sandbox_backend = "bwrap"
   ```
2. Restart Zellij.
3. Spawn a Claude agent.

#### Inside the sandbox
- Command: send a chat message that triggers a real Anthropic API call.
  - Expected: normal response.
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://example.com`
  - Expected: failure — `normal` does not open arbitrary outbound HTTPS.
- Command: `ls ~/.claude/`
  - Expected: access works. `bwrap` uses an isolated copy via the default `use_real_config = false`; behavior is unchanged from pre-merge.

Confirm nothing about pre-merge behavior changed.

### 3.5 Cell: normal x nono (linux) — smoke regression

#### Setup
1. Same as 3.4 with `sandbox_backend = "nono"`.
2. Restart Zellij.
3. Spawn a Claude agent.

#### Inside the sandbox
- Command: send a chat message that triggers a real Anthropic API call.
  - Expected: normal response.
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://example.com`
  - Expected: failure.
- Command: `ls ~/.claude/`
  - Expected: access works (inherited `claude-code` upstream nono preset).

### 3.6 Cell: normal x nono (macOS) — smoke regression

Run only if a macOS host is available. Same commands as 3.5.

### 3.7 Cell: permissive x bwrap (linux)

#### Setup
1. In `~/.config/lince-dashboard/config.toml`:
   ```toml
   [agents.claude]
   sandbox_level = "permissive"
   sandbox_backend = "bwrap"
   ```
2. Restart Zellij.
3. Spawn a Claude agent inside the test project (`/tmp/lince-test`).

#### Inside the sandbox
- Command: `gh auth status`
  - Expected: `Logged in to github.com`. Token reachable via mounted `~/.config/gh`.
- Command: `gh repo view RisorseArtificiali/lince`
  - Expected: repo metadata returned. `api.github.com` is reachable.
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://example.com`
  - Expected: failure. Only allowlisted hosts (Anthropic + GitHub) reach out.
- Command: `docker ps 2>&1`
  - Expected: `command not found` or permission denied. Docker is deliberately excluded.
- Command: `git push origin HEAD 2>&1`
  - Expected: failure (`block_git_push = true` in the bwrap fragment, or no SSH agent in scope).

#### Workflow check
- Have the agent create a branch, commit a small change, and run `gh pr create --fill`.
  - Expected: PR opened against the project's GitHub remote.

### 3.8 Cell: permissive x nono (linux)

#### Setup
1. Same as 3.7 with `sandbox_backend = "nono"`.
2. Restart Zellij.
3. Spawn a Claude agent.

#### Inside the sandbox
- Command: `gh auth status`
  - Expected: `Logged in to github.com`.
- Command: `gh repo view RisorseArtificiali/lince`
  - Expected: repo metadata returned.
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://example.com`
  - Expected: failure.
- Command: `docker ps 2>&1`
  - Expected: `command not found` / not reachable.
- Command: `git push origin HEAD 2>&1`
  - Expected: failure (no SSH agent reachable; HTTPS push blocked unless explicitly added to allowlist).

#### Workflow check
- Have the agent create a branch, commit, and run `gh pr create --fill`.
  - Expected: PR opened.

### 3.9 Cell: permissive x nono (macOS)

Run only if a macOS host is available. Same commands as 3.8.

### 3.10 Cell: paranoid + extra domain via `config.toml` override (linux, bwrap)

Verifies that `allow_domains` is append-merged with the paranoid fragment, so a user can extend the allowlist without writing a custom level.

#### Setup
1. In `~/.agent-sandbox/config.toml` (create the file if absent), add:
   ```toml
   [security]
   allow_domains = ["github.com", "api.github.com", "objects.githubusercontent.com"]
   ```
2. In `~/.config/lince-dashboard/config.toml`:
   ```toml
   [agents.claude]
   sandbox_level = "paranoid"
   sandbox_backend = "bwrap"
   ```
3. Restart Zellij and spawn a Claude agent inside the test project.

#### Inside the sandbox
- Command: `gh auth status`
  - Expected: `Logged in to github.com`. The proxy CONNECT to `api.github.com` is allowed by the extended allowlist; kernel netns isolation is unchanged because traffic still flows through the proxy.
- Command: `curl -s -o /dev/null -w "%{http_code}\n" https://attacker.com 2>&1`
  - Expected: still a kernel-level failure. Extending `allow_domains` does not punch a hole for non-allowlisted hosts.
- Command: `printenv | grep -E "(ANTHROPIC|OPENAI|GEMINI)_API_KEY"`
  - Expected: empty. Credential injection still applies to Anthropic; GitHub traffic passes through without injection.

#### Cleanup
Remove the `[security]` block from `~/.agent-sandbox/config.toml` to return paranoid to its default allowlist.

## 4. Custom-level smoke test

Walk through creating a custom level following the customization story in the design doc.

1. Create the profile file `~/.config/nono/profiles/lince-claude-mytest.json`:
   ```json
   {
     "extends": "lince-claude",
     "meta": {
       "name": "lince-claude-mytest",
       "description": "Custom test level"
     },
     "filesystem": {
       "allow": ["$WORKDIR"],
       "read": ["$HOME/.local/share/test-data"]
     },
     "network": {
       "credentials": ["anthropic"]
     }
   }
   ```
2. Create the matching read-source on the host:
   ```bash
   mkdir -p ~/.local/share/test-data && echo "hello" > ~/.local/share/test-data/marker
   ```
3. In `~/.config/lince-dashboard/agents-defaults.toml` (user override), set:
   ```toml
   [agents.claude]
   sandbox_level = "mytest"
   sandbox_backend = "nono"
   ```
4. Restart Zellij and spawn a Claude agent.
5. Inside the sandbox:
   - Command: `ls ~/.local/share/test-data/`
     - Expected: `marker` is listed.
   - Command: `cat ~/.local/share/test-data/marker`
     - Expected: `hello`.

#### Fallback for typos
1. Set `sandbox_level = "doesnotexist"` in the same override file.
2. Restart Zellij and try to spawn the agent.
3. Expected: the plugin emits a clear error in the pane title or stderr (no profile resolved). The plugin must NOT hard-crash; the dashboard stays responsive.

## 5. Regression checklist

Things that must STILL work after the change.

- N-picker shows **"Claude Code"** once. It must NOT show "Claude Code", "Claude Code (nono)", and "Claude Code (sandboxed)" all at once.
- `[agents.claude-unsandboxed]` is still spawnable. It is a separate entry, not a level.
- Existing agents that have NOT been migrated yet — `codex`, `gemini`, `opencode`, `pi` — still spawn and work as before. They have no `sandbox_level` and fall back to the static command.
- When `sandbox_level` is **not** paranoid (e.g. `permissive` or `normal`), the bwrap sandbox stays in the host network namespace — `--unshare-net` must NOT be set. Verify by running `ip route` from inside a permissive agent shell: it should show the host's default route, not just `lo`. Equivalently, no `socat` bridge process should be spawned for non-paranoid agents (`pgrep -af socat | grep lince-proxy` returns empty).
- `install.sh` is idempotent. Re-running on an already-installed system prints no errors and overwrites profiles cleanly.
- The WASM plugin builds clean:
  ```bash
  cd lince-dashboard/plugin && PATH="$HOME/.cargo/bin:$PATH" $HOME/.cargo/bin/cargo build --release --target wasm32-wasip1
  ```

## 6. Sign-off

Tester ticks each box that was actually run and passed. Cells skipped due to platform unavailability (e.g. macOS) should be left unchecked and noted in the merge description.

- [ ] 3.1 paranoid x bwrap (linux)
- [ ] 3.2 paranoid x nono (linux)
- [ ] 3.3 paranoid x nono (macOS)
- [ ] 3.4 normal x bwrap (linux) — smoke regression
- [ ] 3.5 normal x nono (linux) — smoke regression
- [ ] 3.6 normal x nono (macOS) — smoke regression
- [ ] 3.7 permissive x bwrap (linux)
- [ ] 3.8 permissive x nono (linux)
- [ ] 3.9 permissive x nono (macOS)
- [ ] 3.10 paranoid + extra domain via `config.toml` override (linux, bwrap)
- [ ] 4. Custom-level smoke test (including typo fallback)
- [ ] 5. Regression checklist (all items)
