# lince-lab Bisect — the autonomous regression loop

`lince-lab find bisect` binary-searches a linear range of commits for the first
one that turns a [recipe](recipes.md)'s verdict from **good** (recipe exit 0) to
**bad** (nonzero exit). The recipe is the verdict oracle; the loop runs fully
autonomously — no human in the loop deciding good/bad per step.

```bash
lince-lab find bisect <recipe> \
    --good <ref> --bad <ref> --repo-dir <dir> \
    [--out bisect.json] [--keep]
```

| Flag | Meaning |
|------|---------|
| `<recipe>` | the recipe TOML used as the verdict oracle |
| `--good <ref>` | a ref/sha known to **pass** (exclusive lower bound) |
| `--bad <ref>` | a ref/sha known to **fail** (inclusive upper bound) |
| `--repo-dir <dir>` | the staged repo copy git operates on (never your working tree) |
| `--out <file>` | where to write `bisect.json` (default `./bisect.json`) |
| `--keep` | keep the lab VM after the run (default: delete it) |

## How the loop works

1. **Build one base VM.** The recipe's `[vm]` + `[[provision]]` create, start, and
   provision a single persistent VM, then take a `base-clean` snapshot. This
   happens **once** — provisioning is not repeated per candidate.
2. **Get the candidate list.** `git rev-list --reverse <good>..<bad>` in
   `--repo-dir` yields the commits after `good` up to and including `bad`, oldest
   first.
3. **Binary-search.** For each midpoint candidate:
   - `snapshot apply base-clean` — reset the VM to the identical clean state
     (exactly **one reset per probed candidate**, which guarantees probe
     independence);
   - `git checkout <sha>` in the staged repo, `copy_in` that tree into the VM;
   - run the recipe's steps + asserts (the same oracle `run recipe` uses, minus
     the create/provision/delete lifecycle);
   - recipe exit **0 ⇒ good** (search the upper half), **nonzero ⇒ bad** (record
     it, search the lower half).
4. **Converge** on the first-bad commit. The VM is deleted unless `--keep`.

Because the verdict is just the recipe exit code, a failing exec step or a failed
`[assert]` (a `grid_contains` that never appeared, a `file_exists` that is
missing) is automatically a "bad" verdict — not a crash.

## Example

```console
$ lince-lab find bisect recipes/lince-wizard.toml \
      --good v1.0 --bad HEAD --repo-dir ./my-clone --out bisect.json
first bad commit: c4f1a9e (converged)
```

With `--json` you get the full document on stdout; otherwise it is written to
`--out`.

## `bisect.json`

The machine-readable result (also returned by `bisect.run` over the broker):

```json
{
  "v": 1,
  "recipe": "lince-wizard",
  "good": "abc123",
  "bad": "def456",
  "candidates": ["c1", "c2", "c3", "c4", "c5"],
  "verdicts": [
    {"sha": "c3", "verdict": "good", "exit_code": 0, "step_failed": null,         "duration_s": 41.2},
    {"sha": "c4", "verdict": "bad",  "exit_code": 1, "step_failed": "drive-wizard", "duration_s": 39.8}
  ],
  "first_bad": "c4",
  "status": "converged",
  "tested_count": 2,
  "total_candidates": 5
}
```

| Field | Meaning |
|-------|---------|
| `candidates` | the full ordered commit list searched (oldest first) |
| `verdicts` | one entry per **probed** commit, in probe order — `verdict` is `good`/`bad`, `step_failed` names the failing step when attributable |
| `first_bad` | the first commit that fails the recipe, or `null` |
| `status` | `converged` (found a first-bad), `no_regression` (every candidate good), or `no_candidates` (empty range) |
| `tested_count` / `total_candidates` | how many of the range were actually probed (binary search probes ~log₂N) |

## Tips

- **Use the [`bisect` preset](presets.md).** It retains the base snapshot for fast
  per-candidate reset and gives a long per-step timeout — exactly what the loop
  needs.
- **Pick a recipe whose `[assert]` actually catches the regression** you are
  hunting. The bisect is only as good as its oracle: if the recipe passes on the
  broken commit, the loop will report `no_regression`.
- **`--repo-dir` is staged, not your worktree.** The loop checks out shas in that
  directory; point it at a throwaway clone so your working tree is never touched.
- **Reproducibility is built in.** Each probe starts from the identical
  `base-clean` snapshot, so a flaky-looking result is the recipe's
  non-determinism, not the substrate's — fix it in `[sync]`/`[assert]`.
