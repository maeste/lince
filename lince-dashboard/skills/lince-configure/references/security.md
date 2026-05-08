# Security Model Reference

## Defense Layers (innermost to outermost)

1. **Filesystem isolation** — agent sees only project dir + curated home paths
2. **PID namespace** — agent cannot see host processes (`unshare_pid`)
3. **Network isolation** — kernel-level via netns (bwrap) or Landlock (nono)
4. **Credential proxy** — API keys never enter the sandbox; injected on host side
5. **Git push blocking** — wrapper script in sandbox PATH intercepts `git push`
6. **Environment isolation** — `--clearenv`, only declared vars pass through

## Credential Proxy

When `credential_proxy = true`:
- Host-side proxy listens on a unix socket
- Socket is bind-mounted into sandbox
- Agent routes HTTPS through proxy (`HTTP_PROXY=http://127.0.0.1:8118`)
- Proxy injects `Authorization`/`x-api-key` header on outbound requests
- Proxy enforces `allow_domains` allowlist
- API key is stripped from sandbox environment

Auto-mapped env vars → domains:
- `ANTHROPIC_API_KEY` → `api.anthropic.com`
- `OPENAI_API_KEY` → `api.openai.com`
- `GEMINI_API_KEY` / `GOOGLE_API_KEY` → `googleapis.com`

## Network Namespaces

When `unshare_net = true` (paranoid):
- Agent runs in fresh network namespace (only loopback)
- No route to host or internet
- Proxy reached via bind-mounted unix socket
- `socat` bridges TCP localhost → unix socket inside sandbox
- DNS for non-allowlisted hosts fails at kernel level

## Filesystem Mounts

| Path | Mode | What |
|------|------|------|
| `$PROJECT` | rw | Project working directory |
| `~/.claude` (or scratch) | rw | Agent config (scratch in paranoid) |
| `~/.agent-sandbox/toolchains/` | rw | Build caches |
| `~/.agent-sandbox/bin/git` | ro | Git push blocking wrapper |
| `~/.agent-sandbox/gitconfig` | ro | Sanitized git config |
| `$PATH entries under $HOME` | ro | Auto-exposed tools |
| `home_ro_dirs` entries | ro | User-configured read-only paths |
| `extra_rw` entries | rw | User-configured writable paths |

## Threat Model

| Attack Vector | Mitigation |
|---------------|------------|
| Agent reads SSH keys | Keys not mounted |
| Agent exfiltrates via network | Network namespace isolation |
| Agent reads API key from env | Credential proxy strips keys |
| Agent pushes to git | Git wrapper blocks push |
| Agent modifies host git config | Sanitized copy is read-only |
| Agent escapes via /proc | PID namespace hides host |
| Agent writes to arbitrary paths | Only declared paths are writable |
| Prompt injection via model response | Paranoid: no creds in sandbox to exfiltrate |
