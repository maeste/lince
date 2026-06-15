# lince-lab Recipes

A **recipe** is a TOML file describing one disposable-VM test: which image to
boot, what network posture to allow, the one host directory to stage, the
provision scripts baked into a base snapshot, the ordered steps to drive, and the
mandatory `[assert]` block that decides pass/fail. The same recipe is reused by
[`find bisect`](bisect.md) as the verdict oracle.

Recipes are **read-only inputs** (parsed with `tomllib`). You author them by hand
or copy a shipped one from `~/.local/share/lince/lince-lab/recipes/`. A recipe
declares *needs* only — the broker builds the actual Lima template server-side, so
a recipe can never inject mounts, images, or network rules outside policy.

## Full schema

```toml
[recipe]
name = "lince-wizard"                       # identity; seeds the lince-lab-<name> VM
description = "Drive the lince quickstart wizard to completion and verify config"
version = "1"

[vm]
image = "fedora"                            # must be a key in the config image allowlist
cpus = 2
memory = "2GiB"
disk = "20GiB"

[network]
mode = "deny"                               # "deny" (default) | "allow"
allow_hosts = []                            # e.g. ["registry.npmjs.org"] — REQUIRED if mode="allow"
allow_ports = []                            # e.g. [443]

[workspace]
host_dir = "./fixtures/lince-clone"         # the ONE host dir staged; must resolve under the recipe dir
guest_dir = "/work"                         # where it lands in the VM (default /work)

[[provision]]                               # baked once into the base-clean snapshot
mode = "system"                             # system | user | boot | data
script = "dnf install -y git python3"

[[step]]                                    # an exec step
name = "run-installer"
run = ["sh", "-c", "cd /work && ./quickstart.sh --noninteractive"]

[[step]]                                    # a capture step (driven via ht)
name = "drive-wizard"
capture = true
program = ["lince-config", "quickstart"]
size = "80x24"
keys = ["N", "Enter", "Down", "Enter", "y", "Enter"]   # injected in order, each after a sync

[assert]                                    # REQUIRED — at least one assertion
exit_code = 0                               # the last exec step's exit code must equal this
grid_contains = ["Configuration written"]  # text that MUST appear on the final settled grid
grid_absent  = ["Traceback", "ERROR"]      # text that must NOT appear
file_exists  = ["/work/.config/lince/lince.toml"]   # checked in-guest via `test -f`

[sync]                                       # REQUIRED iff any step has capture = true
wait_for = ["Select agents", "Configuration written"]   # substring to await before each keys batch
stable_ms = 150                              # grid-stability debounce window (event-silence, not sleep)
timeout_s = 60                               # per-wait deadline; exceeding it fails the run
```

## Table reference

| Table | Required? | Keys |
|-------|-----------|------|
| `[recipe]` | yes | `name`, `description`, `version` |
| `[vm]` | yes | `image` (in the config allowlist), `cpus`, `memory`, `disk` |
| `[network]` | optional (default deny) | `mode`, `allow_hosts`, `allow_ports` |
| `[workspace]` | yes | `host_dir` (must resolve under the recipe dir), `guest_dir` |
| `[[provision]]` | optional | `mode`, `script` — baked into the `base-clean` snapshot |
| `[[step]]` | optional | exec: `name`, `run` (argv) · capture: `name`, `capture=true`, `program`, `size`, `keys` |
| `[assert]` | yes (≥ 1 assertion) | `exit_code`, `grid_contains`, `grid_absent`, `file_exists` |
| `[sync]` | required iff any capture step | `wait_for`, `stable_ms`, `timeout_s` |

## Steps: exec vs capture

- **exec step** (`run = [...]`): runs an argv in the guest, capturing its exit
  code. A nonzero exit short-circuits the run and is the recipe's "bad" signal.
- **capture step** (`capture = true`): launches `program` under `ht` inside the
  VM at the given `size`, then for each key in `keys` it first
  `wait_for_substring` (the matching entry in `[sync].wait_for`), then
  `wait_for_stable` (grid settled within `stable_ms`), then sends the key. The
  final settled grid is what `grid_contains` / `grid_absent` assert against.

Capture steps are why `[sync]` is mandatory: synchronization is **event-driven**,
never a fixed sleep — that is what makes driving an interactive wizard
deterministic and fast.

## Assertions

`[assert]` must contain **at least one** of:

| Assertion | Checks |
|-----------|--------|
| `exit_code = N` | the last exec step's exit code equals `N` |
| `grid_contains = [...]` | every substring appears on the final settled terminal grid |
| `grid_absent = [...]` | none of the substrings appears on the final grid |
| `file_exists = [...]` | each path exists in the guest (`test -f`) |

A recipe with no assertion is rejected by validation — it could never be "bad", so
it is useless as an oracle.

## How to author a recipe

1. **Start from a shipped recipe.** Copy one of
   `~/.local/share/lince/lince-lab/recipes/{lince-wizard,lince-installer,generic-npm}.toml`
   into your project next to its `host_dir` fixture.
2. **Set `[recipe]` identity and pick a `[vm].image`** from the config allowlist
   (`lince-lab run presets` and your `~/.config/lince-lab/config.toml` show the
   allowed images; the defaults are `fedora` and `ubuntu`).
3. **Point `[workspace].host_dir` at the one directory to stage.** It must resolve
   **under the recipe file's directory** — `..` or an absolute path outside it is
   rejected (policy bound).
4. **Keep `[network] mode = "deny"`** unless the recipe genuinely fetches. If it
   does, set `mode = "allow"` **and** a non-empty `allow_hosts`/`allow_ports`
   allowlist, and run it under the [`networked`](presets.md) preset. Validation
   rejects `allow` with an empty allowlist.
5. **Add `[[provision]]` for one-time setup** (toolchains); it is baked into the
   `base-clean` snapshot, so it runs once even across bisect candidates.
6. **Add ordered `[[step]]`s.** Use exec steps for scripted commands and capture
   steps for anything interactive.
7. **Write `[assert]`** — at least one assertion, and `[sync]` if you used any
   capture step.
8. **Validate, then run:**

   ```bash
   lince-lab run validate ./my-recipe.toml      # exit 0 = valid, 65 = a schema error (named)
   lince-lab run recipe   ./my-recipe.toml       # exits with the recipe's code
   ```

## Validation rules (exit 65 on failure)

`lince-lab run validate` enforces, with a named error for each:

- a missing `[recipe]` / `[vm]` / `[workspace]` / `[assert]` table;
- an `[assert]` with zero assertions;
- any `capture` step without a `[sync]` section;
- `[network] mode = "allow"` with an empty allowlist;
- a `[workspace].host_dir` that does not resolve under the recipe directory;
- an `image` not in the config's allowed set.

## A non-lince recipe (generic)

Recipes are not lince-specific. `generic-npm.toml` installs and tests an npm
package under the `networked` preset — the same schema, an `allow` network with
an explicit allowlist:

```toml
[recipe]
name = "generic-npm"
description = "Install and test an npm package in an isolated VM"
version = "1"

[vm]
image = "ubuntu"
cpus = 2
memory = "2GiB"

[network]
mode = "allow"
allow_hosts = ["registry.npmjs.org"]
allow_ports = [443]

[workspace]
host_dir = "./pkg"
guest_dir = "/work"

[[provision]]
mode = "system"
script = "apt-get update && apt-get install -y nodejs npm"

[[step]]
name = "install-and-test"
run = ["sh", "-c", "cd /work && npm ci && npm test"]

[assert]
exit_code = 0
```

Run it with: `lince-lab run recipe ./generic-npm.toml` (the broker applies the
`networked` posture: egress is allowed **only** to `registry.npmjs.org:443`,
everything else stays denied, and no host credentials are injected).
