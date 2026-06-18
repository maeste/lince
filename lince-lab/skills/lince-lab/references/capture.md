# Reference: Capture — driving an interactive TUI deterministically

To drive an interactive program (a wizard, a prompt-driven installer), use a
**capture step** in a recipe, or the `watch` verbs ad hoc. Synchronization is
**event-driven** — you wait for a substring or for the grid to settle, never for a
fixed number of seconds.

## In a recipe (preferred)

```toml
[[step]]
name = "drive-wizard"
capture = true
program = ["lince-config", "quickstart"]   # runs under `ht` inside the VM
size = "80x24"
keys = ["N", "Enter", "Down", "Enter", "y", "Enter"]   # sent in order

[sync]                                       # REQUIRED whenever capture = true
wait_for = ["Select agents", "Confirm", "Configuration written"]
stable_ms = 150        # grid must be silent this long before the next key
timeout_s = 60         # per-wait deadline; exceeding it FAILS the run

[assert]
grid_contains = ["Configuration written"]
grid_absent  = ["Traceback"]
```

Per key, the runner: waits for the matching `wait_for[i]` substring → waits for
the grid to stop changing (`stable_ms`) → sends the key. The final settled grid is
what `grid_contains` / `grid_absent` assert against.

## Ad hoc with `watch`

```bash
# Snapshot the current terminal grid:
lince-lab watch grab <vm> --program top

# Send keys:
lince-lab watch keys <vm> --program lince-config quickstart --keys N Enter

# Wait for a substring, then print the settled grid:
lince-lab watch wait <vm> --program lince-config quickstart \
    --for "Select agents" --cmd-timeout 30

# Wait until the grid stops changing:
lince-lab watch wait <vm> --program some-tui --stable --stable-ms 200
```

`watch wait` needs exactly one of `--for SUBSTR` or `--stable`.

## Rules

- **Never insert a `sleep`** to "let the screen catch up". Use `wait_for` (a prompt
  you expect) and `stable_ms` (the grid settling). That is what makes the run
  deterministic and fast.
- **Match `wait_for` entries to your keys.** The i-th key waits for `wait_for[i]`
  if present; order matters.
- **Assert on the grid, not on timing.** Put the prompt/result text you expect in
  `grid_contains`, and failure indicators (`Traceback`, `ERROR`) in `grid_absent`.
- **The grid is text.** `lince-lab` v1 captures the rendered terminal text grid
  (one line per row) — there is no pixel/image capture; assert on substrings.
