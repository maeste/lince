# Sandbox Levels Reference

Three isolation levels, selectable per agent per run.

## Comparison

| Aspect | paranoid | normal | permissive |
|--------|----------|--------|------------|
| **Network** | Kernel-isolated (netns/Landlock) | Inherited | Open |
| **Credential proxy** | Required (API keys on host only) | Opt-in | Off by default |
| **Home dirs** | Scratch (per-run, ephemeral) | Standard mounts | + gh, cache, known_hosts |
| **gh CLI** | No | No | Yes |
| **git push** | Blocked | Blocked | Blocked (use gh) |
| **Use when** | Untrusted input, unfamiliar repos | Daily work | Need PRs/GitHub from agent |

## Selecting a Level

Per run (CLI):
```bash
agent-sandbox run --sandbox-level paranoid
agent-sandbox run --sandbox-level permissive -a codex
```

Per agent (dashboard config):
```bash
lince-config set agents.claude.sandbox_level "paranoid" --target dashboard -q
```

## Paranoid Details

- `unshare_net = true` + `credential_proxy = true`
- Only API endpoint reachable (api.anthropic.com, api.openai.com, etc.)
- Agent's config dir is a per-run scratch copy (rsync-seeded, discarded on exit)
- API key never enters the sandbox process tree
- **Requires** an API key on the host (not OAuth)
- **Requires** `socat` installed (for bwrap backend)

Extend allowlist without forking the level:
```bash
lince-config append security.allow_domains "pypi.org" -q
lince-config append security.allow_domains "files.pythonhosted.org" -q
```

## Permissive Details

- Network open, credential proxy off by default
- `~/.config/gh` read-only (gh finds its token)
- `~/.cache` read-only (tool cache reuse)
- `~/.ssh/known_hosts` read-only (SSH remotes work)
- `git push` still blocked — use `gh pr create` instead
- Recommended: fine-grained PAT scoped to specific repos

## Custom Levels

Any string works as a level name, as long as a profile fragment exists:

- bwrap: `~/.agent-sandbox/profiles/<level>.toml` or `<agent>-<level>.toml`
- nono: `~/.config/nono/profiles/lince-<agent>-<level>.json`

Fragments support `extends` for inheritance:
```toml
# ~/.agent-sandbox/profiles/paranoid-with-ssh.toml
extends = "paranoid"

[sandbox]
home_ro_dirs = [".ssh"]
```

## Per-Agent Quirks

### Claude
- `[claude] use_real_config` only applies at normal/permissive
- Paranoid always uses scratch (ignores use_real_config)

### Codex
- `bwrap_conflict = true` — always needs `--sandbox danger-full-access`
- `~/.codex` is scratch in paranoid

### Gemini
- Paranoid requires API key auth (not OAuth/browser login)
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` must be set on host

## Trust Model

| Property | Paranoid + API key | Paranoid + OAuth | Normal/Permissive |
|----------|-------------------|------------------|-------------------|
| Kernel network isolation | ✅ | ✅ | ❌ |
| Credentials never in sandbox | ✅ | ❌ | ❌ |
| Prompt injection can exfiltrate creds | No | Yes | Depends |

OAuth users should use `normal` or `permissive`, not `paranoid`.
