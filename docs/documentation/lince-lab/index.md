# lince-lab

**Disposable lab VMs for autonomous testing and regression hunting.**

`lince-lab` gives an agent (or you) a throwaway virtual machine it can create,
boot, drive, snapshot, reset, and destroy — without ever touching your host
filesystem or your real Lima VMs, and without being trusted to relax its own
isolation. It is the substrate behind autonomously verifying a fix, driving the
lince quickstart wizard to completion, checking `install.sh` idempotency, and
**bisecting** a regression across a range of commits.

## What it is

| Piece | Role |
|-------|------|
| **CLI** `lince-lab` | one argparse command, five verb groups (`vm` / `run` / `find` / `watch` / `lab`) |
| **Broker** | a host-side process the agent commands over a narrow unix socket; the agent never gets the VM filesystem |
| **Backend** | the substrate seam: `LimaBackend` (real, QEMU on Linux) or `FakeBackend` (in-memory, for tests) |
| **Recipe** | a TOML file describing a VM test — image, network posture, one staged workspace, ordered steps, and a mandatory `[assert]` block |
| **Bisect** | `find bisect` reuses a recipe as the verdict oracle to binary-search the first-bad commit |
| **Capture** | drive an interactive TUI deterministically (`ht` inside the VM, event-driven waits, no fixed sleeps) |

## Why use it

- **Isolated by default.** VMs boot `--plain` with no host mounts; the network is
  **deny-by-default**; host credentials are never injected. A recipe opts into
  egress only with an explicit allowlist.
- **Deterministic.** Terminal synchronization is event-driven
  (`wait_for_substring` / `wait_for_stable`), never `sleep` — driving a wizard is
  fast and repeatable.
- **Exit codes are the signal.** A failing guest command or recipe propagates its
  exit code straight through to the CLI, so `lince-lab` composes in shell pipelines
  and powers the bisect verdict.
- **Agent-safe.** The agent commands the broker over a closed verb whitelist; there
  is no raw-shell escape. Every policy decision is made host-side from the recipe's
  declared needs, never from client-supplied data.

## Quick start

```bash
# 1. Install (idempotent).
lince-lab/install.sh

# 2. Start the host-side broker (leave it running).
lince-lab lab broker start &

# 3. Check prerequisites.
lince-lab lab doctor

# 4. Validate then run a recipe end-to-end.
lince-lab run validate recipes/lince-wizard.toml
lince-lab run recipe   recipes/lince-wizard.toml      # exits with the recipe's code

# 5. Hunt a regression (recipe = verdict oracle).
lince-lab find bisect recipes/lince-wizard.toml \
    --good v1.0 --bad HEAD --repo-dir ./my-clone --out bisect.json
```

## Prerequisites

- Linux with `/dev/kvm` access (member of the `kvm` group).
- `limactl` (Lima) + `qemu-img` (Fedora: `sudo dnf install qemu-kvm qemu-img`,
  then install Lima per its docs). `lince-lab lab doctor` reports what is missing.
- Python 3.11+ (for the CLI and broker).

`ht` (the headless terminal used for capture) is installed inside the VM by a
recipe provision step — you do not install it on the host.

## Where things live

| Path | Contents |
|------|----------|
| `~/.local/bin/lince-lab` | the CLI |
| `~/.local/share/lince/lince-lab/{lince_lab,recipes,templates}/` | package + shipped recipes + Lima template |
| `~/.claude/skills/lince-lab/` | the agent skill |
| `~/.config/lince-lab/config.toml` | your config (created only if absent; optional) |
| `~/.agent-sandbox/lince-lab.sock` | the runtime broker socket |

## Documentation map

- **[CLI reference](cli.md)** — the five groups, every verb, multi-level help, example output.
- **[Recipes](recipes.md)** — the TOML schema and how to author one.
- **[Presets](presets.md)** — `quick`, `bisect`, `networked`, and when to use each.
- **[Bisect](bisect.md)** — the autonomous regression loop and `bisect.json`.
- **[Design doc / ADRs](https://github.com/RisorseArtificiali/lince/blob/main/docs/design/lince-lab-design.md)** — the authoritative architecture (ADR-01..ADR-10).
