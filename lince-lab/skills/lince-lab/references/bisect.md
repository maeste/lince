# Reference: Bisect (autonomous regression hunting)

`find bisect` binary-searches commits for the first one that fails a recipe. The
recipe is the verdict oracle: exit 0 = good, nonzero = bad.

```bash
lince-lab find bisect <recipe> \
    --good <known-good-ref> \
    --bad  <known-bad-ref> \
    --repo-dir <staged-clone> \
    --out bisect.json
```

| Flag | Meaning |
|------|---------|
| `--good` | a ref/sha known to PASS (exclusive lower bound) |
| `--bad` | a ref/sha known to FAIL (inclusive upper bound) |
| `--repo-dir` | the staged clone git checks out shas in — NEVER your working tree |
| `--out` | `bisect.json` path (default `./bisect.json`) |
| `--keep` | keep the VM after the run |

## How to use it well

1. **Pick a recipe whose `[assert]` actually catches the bug.** If the recipe
   passes on the broken commit, the result is `no_regression` — the oracle is too
   weak. Tighten `grid_contains` / `file_exists` / `exit_code` until the known-bad
   ref reports "bad" and the known-good ref reports "good".
2. **Use a throwaway clone for `--repo-dir`.** The loop runs `git checkout`
   there; do not point it at a dirty worktree.
3. **Prefer the `bisect` preset** (base snapshot retained → fast per-candidate
   reset; long step timeout).

## Read `bisect.json`

```json
{
  "first_bad_commit": "c4f1a9e",
  "first_bad": "c4f1a9e",
  "status": "converged",
  "candidates": ["c1", "c2", "c3", "c4", "c5"],
  "verdicts": [
    {"sha": "c3", "verdict": "good", "exit_code": 0, "step_failed": null},
    {"sha": "c4", "verdict": "bad",  "exit_code": 1, "step_failed": "drive-wizard"}
  ],
  "tested_count": 2,
  "total_candidates": 5
}
```

| Read | To learn |
|------|----------|
| `first_bad_commit` | the commit to report (or `null` if none) — the canonical field |
| `first_bad` | back-compat alias of `first_bad_commit` (same value) |
| `status` | `converged` / `no_regression` / `no_candidates` |
| `verdicts[].step_failed` | which recipe step the bad commit broke |

`first_bad_commit` and `first_bad` always carry the same value; read either.

Report `first_bad_commit` and the failing step. If `status` is `no_regression`, the
range did not contain the break **as the recipe defines it** — re-check the
recipe's assertions or the good/bad bounds before concluding.
