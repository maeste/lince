# lince-lab Presets

A **preset** is a named bundle of resource / network / lifecycle knobs that tunes
a lab VM for a common job. Presets exist so you do not have to set five
individual knobs for the everyday postures. List them at any time:

```console
$ lince-lab run presets
bisect: Tuned for the autonomous regression loop ...
networked: For recipes that legitimately must fetch (npm/pip) ...
quick: Fast, minimal disposable VM for smoke-testing a single command ...
```

## What presets do — and what they cannot do

Presets carry **only** resource (CPU / memory / disk), network mode, and
lifecycle (auto-delete, base-snapshot retention, per-step timeout) settings.

They **cannot** weaken the security invariants. No host mounts, no host-credential
injection, and the `lince-lab-*` VM-name namespace are **policy**, not config —
they are enforced broker-side and are not preset knobs. The `networked` preset
only widens egress to a recipe's *own* declared allowlist; it can never inject
credentials or drop the metadata-endpoint block.

## The three presets

### `quick` — smoke-test a single command or recipe

| Knob | Value |
|------|-------|
| CPU / memory / disk | 1 CPU / 1GiB / 10GiB |
| network | **deny** |
| base snapshot | not retained |
| lifecycle | VM auto-deleted after the run |
| per-step timeout | 120s |

**Use it when** you just want to know *does this install/recipe run at all* on a
clean machine. Minimal footprint, fastest spin-up, fully offline.

### `bisect` — the autonomous regression loop

| Knob | Value |
|------|-------|
| CPU / memory / disk | 2 CPU / 2GiB / 20GiB |
| network | **deny** |
| base snapshot | **retained** (fast per-candidate reset) |
| lifecycle | VM deleted at the end of the run |
| per-step timeout | 600s |

**Use it with** [`find bisect`](bisect.md). Retaining the `base-clean` snapshot is
the point: every candidate commit resets to the identical provisioned state via
`snapshot apply` instead of re-provisioning, so a long bisect stays fast and each
probe is independent. The longer step timeout absorbs slow builds.

### `networked` — recipes that legitimately must fetch

| Knob | Value |
|------|-------|
| CPU / memory / disk | 2 CPU / 2GiB / 20GiB |
| network | **allow** — but only the recipe's explicit `allow_hosts`/`allow_ports` |
| base snapshot | not retained |
| lifecycle | VM auto-deleted after the run |
| per-step timeout | 300s |

**Use it for** recipes that must reach a package registry (`npm ci`, `pip
install`). Egress is still deny-by-default for everything; only the hosts/ports
the recipe declares are reachable, and they are reachable **only** through the
broker-compiled rule — no host credentials are injected, and cloud-metadata
endpoints stay blocked. A recipe under this preset must set `[network] mode =
"allow"` with a non-empty allowlist, or validation rejects it.

## Choosing a preset

| Your goal | Preset |
|-----------|--------|
| "does this command/recipe even run?" | `quick` |
| "which commit broke this?" | `bisect` |
| "this recipe needs to `npm ci` / `pip install`" | `networked` |

If you set nothing, the baked defaults apply: 2 CPU / 2GiB / 20GiB, network deny,
auto-delete — equivalent to a middle ground suitable for most single-shot recipe
runs.

## Where presets and defaults come from

Defaults and presets live in the CLI's `config.py`; you can override the
**defaults** (not the security invariants) in `~/.config/lince-lab/config.toml`:

```toml
# ~/.config/lince-lab/config.toml — created by install.sh only if absent
lima_version = "v1.1.0"
capture_tool = "ht"
grid_size = "80x24"

[vm]
cpus = 2
memory = "2GiB"
disk = "20GiB"

[network]
mode = "deny"

# The image allowlist — a recipe can only request a key listed here.
[images.fedora]
location = "https://.../Fedora-Cloud-Base-...x86_64.qcow2"
arch = "x86_64"
```

The config file is **optional** — every key has a sane baked default, so a
non-expert can run `lince-lab run recipe X` with no config at all.
