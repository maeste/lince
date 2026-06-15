# Reference: Presets

A preset tunes resource / network / lifecycle knobs. It **cannot** weaken
security (no host mounts, no credential injection, the `lince-lab-*` name
namespace are policy, not config). List them:

```bash
lince-lab run presets
```

| Preset | Use when | Knobs |
|--------|----------|-------|
| `quick` | "does this even run?" — single command/recipe smoke test | 1 CPU / 1GiB / 10GiB, deny, no base snapshot, auto-delete |
| `bisect` | with `find bisect` — the regression loop | 2 CPU / 2GiB, deny, **base snapshot retained** (fast reset), long step timeout |
| `networked` | recipe must fetch (`npm ci`, `pip install`) | 2 CPU / 2GiB, **allow** but only the recipe's own allowlist, no host creds |

## Decision

- Verifying a fix or idempotency offline → `quick` (or just the defaults).
- Hunting which commit broke something → `bisect`.
- Recipe genuinely needs a package registry → `networked`, and the recipe MUST
  declare `[network] mode = "allow"` with a non-empty `allow_hosts`/`allow_ports`.

## Defaults (no preset)

If you pick no preset, the baked defaults apply (2 CPU / 2GiB / 20GiB, network
deny, auto-delete) — fine for most single-shot recipe runs. The config file
`~/.config/lince-lab/config.toml` is optional; never edit shipped data to change
defaults.

## What `networked` does NOT do

It widens egress only to the hosts/ports the recipe declares, routed through the
broker-compiled rule. It never injects host credentials and never unblocks cloud
metadata endpoints. If you need a host that is not in the recipe's allowlist, add
it to the recipe's `allow_hosts` — do not look for a way to disable the policy.
