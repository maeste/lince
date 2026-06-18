# Reference: Writing a recipe

A recipe is a TOML file you author next to its fixture, then run with
`lince-lab run recipe <file>`. It declares *needs* only — the broker builds the
VM template server-side.

## Minimal recipe (exec-only)

```toml
[recipe]
name = "smoke"
description = "Does install.sh run on a clean machine?"
version = "1"

[vm]
image = "fedora"        # must be in the config image allowlist (fedora|ubuntu by default)

[workspace]
host_dir = "./fixture"  # the ONE staged dir; MUST resolve under this recipe's directory
guest_dir = "/work"

[[step]]
name = "install"
run = ["sh", "-c", "cd /work && ./install.sh"]

[assert]
exit_code = 0
```

## Required vs optional

| Table | Required | Notes |
|-------|----------|-------|
| `[recipe]` | yes | `name` seeds the `lince-lab-<name>` VM |
| `[vm]` | yes | `image` (allowlisted), optional `cpus`/`memory`/`disk` |
| `[workspace]` | yes | `host_dir` must resolve under the recipe dir |
| `[assert]` | yes | at least one of `exit_code`, `grid_contains`, `grid_absent`, `file_exists` |
| `[network]` | optional | defaults to deny; `mode="allow"` REQUIRES an allowlist |
| `[[provision]]` | optional | baked once into `base-clean` (toolchains) |
| `[[step]]` | optional | exec (`run`) or capture (`capture=true`) |
| `[sync]` | required iff a capture step exists | `wait_for`, `stable_ms`, `timeout_s` |

## Idempotency check pattern

To assert `install.sh` is idempotent, run it twice and assert the second run is a
clean no-op:

```toml
[[step]]
name = "first-install"
run = ["sh", "-c", "cd /work && ./install.sh"]

[[step]]
name = "second-install-is-noop"
run = ["sh", "-c", "cd /work && ./install.sh"]

[assert]
exit_code = 0
grid_absent = ["already exists", "ERROR"]
```

## Validation (do this before every run)

```bash
lince-lab run validate ./recipe.toml
```

Exit 0 = valid. Exit 65 names exactly what to fix: a missing required table, an
empty `[assert]`, a capture step without `[sync]`, `mode="allow"` with an empty
allowlist, a `host_dir` that escapes the recipe dir, or an unknown image.

## Then run

```bash
lince-lab run recipe ./recipe.toml      # exits with the recipe's code
lince-lab run recipe ./recipe.toml --keep   # keep the VM for inspection
```
