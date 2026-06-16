"""Autonomous regression hunting — the bisect loop (blueprint §6).

A *bisect* binary-searches a linear range of commits for the first one that
turns a recipe's verdict from "good" (recipe exit 0) to "bad" (nonzero). The
recipe's run-flow is the verdict oracle: each candidate commit is staged into a
single persistent lab VM, the recipe steps + asserts run, and the resulting exit
code decides the verdict.

The substrate is reset between candidates by a snapshot taken once after
provisioning (``base-clean``) — so each probe starts from an identical clean
state. ``snapshot_apply`` is therefore called exactly once per probed candidate;
``test_bisect`` asserts that to guard reset correctness.

Testability is the load-bearing design choice. The two impure dependencies — the
ordered commit list (``git rev-list``) and the per-candidate verdict (checkout +
``copy_in`` + ``run_recipe``) — are *injected*. ``run_bisect`` defaults them to
the real git + recipe runner, but a unit test supplies a seeded commit list and a
verdict function that flips to "bad" at a known sha, so the whole search runs
against ``FakeBackend`` with no git and no VM.

Result shape (``bisect.json``)::

    {
      "v": 1, "recipe": "...", "good": "...", "bad": "...",
      "candidates": ["c1", ...],
      "verdicts": [{"sha": "...", "verdict": "good|bad", "exit_code": N,
                    "step_failed": str|None, "duration_s": F}, ...],
      "first_bad": "c4" | None,            # back-compat alias
      "first_bad_commit": "c4" | None,     # the AC (#258) literal field name
      "status": "converged" | "no_candidates" | "no_regression",
      "tested_count": N, "total_candidates": M
    }

Both ``first_bad`` and ``first_bad_commit`` are always present and carry the same
value; consumers may read either.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lince_lab.backend import Backend
from lince_lab.errors import BackendError, DataError
from lince_lab.paths import slug_vm_name
from lince_lab.recipe import (
    BASE_SNAPSHOT_TAG,
    Recipe,
    recipe_needs,
    run_steps_and_assert,
    step_timeout_of,
    validate,
)
from lince_lab.templates import build_template

# A provider of the ordered candidate commit list for a good..bad range. The
# default shells `git rev-list --reverse good..bad`; a test injects a list.
CommitProvider = Callable[[str, str, Path], list[str]]

# A per-candidate verdict runner. Given a sha it stages that commit into the VM
# and runs the recipe, returning the verdict outcome. The default checks out the
# sha in the staged repo, copies it in, and runs the recipe; a test injects a
# function that flips to "bad" at a known sha. ``backend`` and ``vm_name`` let
# the default reach the persistent VM; the search calls ``snapshot_apply`` to
# reset *before* invoking this for each candidate.
VerdictRunner = Callable[[str], "Verdict"]


@dataclass
class Verdict:
    """The outcome of running the recipe against one candidate commit.

    ``verdict`` is ``"good"`` iff ``exit_code == 0``. ``step_failed`` names the
    recipe step that failed (when the runner can attribute it), else ``None``.
    ``duration_s`` is wall-clock seconds for the probe.
    """

    sha: str
    exit_code: int
    step_failed: str | None = None
    duration_s: float = 0.0

    @property
    def verdict(self) -> str:
        return "good" if self.exit_code == 0 else "bad"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "verdict": self.verdict,
            "exit_code": self.exit_code,
            "step_failed": self.step_failed,
            "duration_s": round(self.duration_s, 3),
        }


def git_rev_list(good: str, bad: str, repo_dir: Path) -> list[str]:
    """Default commit provider: ``git rev-list --reverse good..bad`` in ``repo_dir``.

    Returns the candidate commits in chronological order (oldest first), i.e.
    the commits *after* ``good`` up to and including ``bad``. Raises
    :class:`~lince_lab.errors.DataError` (exit 65) if git fails — a bad ref or a
    non-repo directory is a data problem, not a backend failure.
    """
    proc = subprocess.run(
        ["git", "rev-list", "--reverse", f"{good}..{bad}"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise DataError(f"git rev-list {good}..{bad} failed: {proc.stderr.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _git_checkout(sha: str, repo_dir: Path) -> None:
    """Check out ``sha`` in the staged repo copy (default verdict runner helper)."""
    proc = subprocess.run(
        ["git", "checkout", "--quiet", sha],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise DataError(f"git checkout {sha} failed: {proc.stderr.strip()}")


def _default_verdict_runner(
    backend: Backend,
    recipe: Recipe,
    config: dict[str, Any],
    repo_dir: Path,
    vm_name: str,
) -> VerdictRunner:
    """Build the real per-candidate verdict runner against the *persistent* VM.

    The bisect VM is created, provisioned and snapshotted once by
    :func:`_build_base_vm`; this runner reuses it for every candidate rather than
    re-creating one per probe (the per-probe reset is the search's
    ``snapshot_apply(base-clean)``). For each candidate it checks out the sha in
    the staged ``repo_dir``, copies that staged tree into the VM, runs the
    recipe's steps + asserts (the same step/assert logic ``run_recipe`` uses,
    minus the create/provision/delete lifecycle), and returns a :class:`Verdict`
    carrying the recipe exit code. A nonzero exit or an assertion mismatch is the
    "bad" signal, not an error.
    """
    guest_dir = str(recipe.workspace.get("guest_dir", "/work"))
    step_timeout = step_timeout_of(config)

    def run(sha: str) -> Verdict:
        started = time.monotonic()
        _git_checkout(sha, repo_dir)
        backend.copy_in(vm_name, str(repo_dir), guest_dir, recursive=True)
        try:
            exit_code, step_failed = run_steps_and_assert(backend, recipe, vm_name, step_timeout=step_timeout)
        except DataError as exc:
            # A grid/file assertion mismatch is a "bad" verdict, not a crash.
            exit_code, step_failed = exc.exit_code, "assert"
        duration = time.monotonic() - started
        return Verdict(sha=sha, exit_code=exit_code, step_failed=step_failed, duration_s=duration)

    return run


def _bisect_vm_name(recipe: Recipe) -> str:
    """The persistent VM name used across all candidates of a bisect run."""
    return slug_vm_name(recipe.name, prefix="lince-lab-bisect-")


def run_bisect(
    backend: Backend,
    recipe: Recipe,
    config: dict[str, Any],
    good: str,
    bad: str,
    repo_dir: str | Path,
    out_path: str | Path = "bisect.json",
    *,
    commit_provider: CommitProvider | None = None,
    verdict_runner: VerdictRunner | None = None,
    keep: bool = False,
) -> dict[str, Any]:
    """Bisect ``good..bad`` for the first commit that fails ``recipe``.

    Builds one persistent base VM (``create`` → ``start`` → provision →
    ``snapshot_create(base-clean)``), obtains the ordered candidate list, and
    binary-searches it. Each probed candidate is preceded by a
    ``snapshot_apply(base-clean)`` reset, then staged + verdicted; recipe exit 0
    ⇒ good (search the upper half), nonzero ⇒ bad (search the lower half),
    converging on the first-bad commit.

    ``commit_provider`` and ``verdict_runner`` are injected for testability and
    default to :func:`git_rev_list` and the real recipe-driven runner. Writes the
    ``bisect.json`` document to ``out_path`` and returns the same dict.

    Args:
        good: a ref/sha known to pass (exclusive lower bound).
        bad: a ref/sha known to fail (inclusive upper bound).
        repo_dir: the staged repo copy git operates on (never the host worktree).
        out_path: where to write ``bisect.json`` (default ``./bisect.json``).
        keep: keep the lab VM after the run (default: delete it).
    """
    validate(recipe, config)
    repo_path = Path(repo_dir)
    provider = commit_provider or (lambda g, b, r: git_rev_list(g, b, r))

    candidates = provider(good, bad, repo_path)

    vm_name = _bisect_vm_name(recipe)
    # True iff this run created the persistent base VM itself (the default path).
    # An injected verdict_runner brings its own substrate, so we neither build,
    # reset, nor delete a VM in that case. This single flag drives all three.
    owns_base_vm = False
    runner = verdict_runner
    try:
        if runner is None:
            _build_base_vm(backend, recipe, config, vm_name)
            owns_base_vm = True
            runner = _default_verdict_runner(backend, recipe, config, repo_path, vm_name)

        verdicts, first_bad, status = _search(backend, vm_name, candidates, runner, owns_base_vm=owns_base_vm)
    finally:
        if owns_base_vm and not keep:
            _safe_delete(backend, vm_name)

    document = _build_document(recipe, good, bad, candidates, verdicts, first_bad, status)
    Path(out_path).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document


def _build_base_vm(
    backend: Backend,
    recipe: Recipe,
    config: dict[str, Any],
    vm_name: str,
) -> None:
    """Create + start the persistent VM, provision it, and snapshot ``base-clean``."""
    template_yaml = build_template(config, recipe_needs(recipe))
    backend.create(vm_name, template_yaml)
    backend.start(vm_name)
    for entry in recipe.provision:
        script = entry.get("script")
        if script:
            backend.exec(vm_name, ["sh", "-c", str(script)])
    backend.snapshot_create(vm_name, BASE_SNAPSHOT_TAG)


def _search(
    backend: Backend,
    vm_name: str,
    candidates: list[str],
    runner: VerdictRunner,
    *,
    owns_base_vm: bool,
) -> tuple[list[Verdict], str | None, str]:
    """Binary-search ``candidates`` for the first-bad commit.

    Invariant: everything strictly below ``lo`` is good, everything at/above
    ``hi`` is bad. Each probe resets the VM with ``snapshot_apply(base-clean)``
    *before* running the verdict (when ``owns_base_vm`` — i.e. this run owns a real
    base snapshot). The reset is therefore performed exactly once per probed
    candidate.

    Returns ``(verdicts_in_probe_order, first_bad_sha_or_None, status)``.
    """
    if not candidates:
        return [], None, "no_candidates"

    verdicts: list[Verdict] = []
    lo, hi = 0, len(candidates) - 1
    first_bad: str | None = None

    while lo <= hi:
        mid = (lo + hi) // 2
        sha = candidates[mid]

        if owns_base_vm:
            # Reset to the clean base before staging this candidate.
            backend.snapshot_apply(vm_name, BASE_SNAPSHOT_TAG)

        verdict = runner(sha)
        verdicts.append(verdict)

        if verdict.verdict == "bad":
            first_bad = sha
            hi = mid - 1
        else:
            lo = mid + 1

    status = "converged" if first_bad is not None else "no_regression"
    return verdicts, first_bad, status


def _build_document(
    recipe: Recipe,
    good: str,
    bad: str,
    candidates: list[str],
    verdicts: list[Verdict],
    first_bad: str | None,
    status: str,
) -> dict[str, Any]:
    """Assemble the ``bisect.json`` dict (blueprint §6 shape)."""
    return {
        "v": 1,
        "recipe": recipe.name,
        "good": good,
        "bad": bad,
        "candidates": list(candidates),
        "verdicts": [v.to_dict() for v in verdicts],
        # ``first_bad_commit`` is the AC's (#258) literal field name; ``first_bad``
        # is kept as a back-compat alias. Both carry the same value (or None).
        "first_bad": first_bad,
        "first_bad_commit": first_bad,
        "status": status,
        "tested_count": len(verdicts),
        "total_candidates": len(candidates),
    }


def _safe_delete(backend: Backend, vm_name: str) -> None:
    """Delete the lab VM, swallowing a backend error so cleanup never masks a result."""
    try:
        backend.delete(vm_name, force=True)
    except BackendError:
        pass
