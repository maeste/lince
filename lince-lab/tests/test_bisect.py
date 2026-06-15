#!/usr/bin/env python3
"""Bisect loop tests (blueprint §6).

Two layers of coverage, both VM-free and git-free:

* **Search algorithm** — inject a candidate list and a verdict function that
  flips to "bad" at a known sha; assert convergence on the correct first-bad
  commit across several list shapes (flip in the middle, at the ends, all-good,
  all-bad, single candidate, empty range).
* **Reset + integration** — drive the *default* path (the one that owns a real
  base VM) against ``FakeBackend`` with git monkeypatched out, asserting:
  ``snapshot_apply(base-clean)`` is called exactly once per probed candidate
  (reset correctness); the recipe-driven verdict is honored via a regression
  seeded into the Fake's virtual filesystem; and the ``bisect.json`` document has
  the blueprint shape and is written to disk.

Run with:
    python3 lince-lab/tests/test_bisect.py
"""

import json
import pathlib
import sys
import tempfile
import unittest

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab import bisect as bisect_mod  # noqa: E402
from lince_lab.backend import ExecResult, VmStatus  # noqa: E402
from lince_lab.bisect import Verdict, run_bisect  # noqa: E402
from lince_lab.fake_backend import FakeBackend  # noqa: E402
from lince_lab.recipe import BASE_SNAPSHOT_TAG, Recipe  # noqa: E402

CONFIG = {
    "vm": {"cpus": 2, "memory": "2GiB", "disk": "20GiB"},
    "images": {
        "fedora": {"location": "https://example/Fedora.qcow2", "arch": "x86_64", "digest": ""},
    },
}


def make_recipe(source_dir: pathlib.Path, **overrides) -> Recipe:
    """Build a valid baseline :class:`Recipe` for bisect runs."""
    base = {
        "name": "demo",
        "description": "demo recipe",
        "version": "1",
        "vm": {"image": "fedora", "cpus": 2, "memory": "2GiB", "disk": "20GiB"},
        "network": {"mode": "deny", "allow_hosts": [], "allow_ports": []},
        "workspace": {"host_dir": ".", "guest_dir": "/work"},
        "assertions": {"exit_code": 0},
        "provision": [{"mode": "system", "script": "install deps"}],
        "steps": [{"name": "run-test", "run": ["make", "test"]}],
        "sync": {},
        "source_dir": source_dir,
    }
    base.update(overrides)
    return Recipe(**base)


class SearchAlgorithmTest(unittest.TestCase):
    """Binary-search convergence with an injected verdict function."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.backend = FakeBackend()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, candidates, first_bad_sha, out_name="bisect.json"):
        """Run a bisect with injected list + verdict flipping bad at ``first_bad_sha``.

        ``first_bad_sha`` may be ``None`` to mean "every candidate is good".
        Returns ``(document, probed_shas)``.
        """
        recipe = make_recipe(self.dir)
        probed: list[str] = []

        bad_index = candidates.index(first_bad_sha) if first_bad_sha is not None else len(candidates)

        def verdict_runner(sha: str) -> Verdict:
            probed.append(sha)
            idx = candidates.index(sha)
            # "bad" for every candidate at/after the regression point.
            exit_code = 1 if idx >= bad_index else 0
            return Verdict(sha=sha, exit_code=exit_code, step_failed="run-test" if exit_code else None)

        out_path = self.dir / out_name
        doc = run_bisect(
            self.backend,
            recipe,
            CONFIG,
            good="g",
            bad="b",
            repo_dir=self.dir,
            out_path=out_path,
            commit_provider=lambda g, b, r: list(candidates),
            verdict_runner=verdict_runner,
        )
        return doc, probed

    def test_flip_in_middle(self) -> None:
        candidates = ["c1", "c2", "c3", "c4", "c5"]
        doc, probed = self._run(candidates, "c4")
        self.assertEqual(doc["first_bad"], "c4")
        self.assertEqual(doc["status"], "converged")
        # Binary search probes a logarithmic number of candidates, never all 5.
        self.assertLessEqual(doc["tested_count"], 4)
        self.assertEqual(doc["total_candidates"], 5)
        # Every verdict before c4 is good, c4 and after that are bad.
        for v in doc["verdicts"]:
            idx = candidates.index(v["sha"])
            self.assertEqual(v["verdict"], "bad" if idx >= 3 else "good")

    def test_flip_at_first_candidate(self) -> None:
        candidates = ["c1", "c2", "c3", "c4", "c5"]
        doc, _ = self._run(candidates, "c1")
        self.assertEqual(doc["first_bad"], "c1")
        self.assertEqual(doc["status"], "converged")

    def test_flip_at_last_candidate(self) -> None:
        candidates = ["c1", "c2", "c3", "c4", "c5"]
        doc, _ = self._run(candidates, "c5")
        self.assertEqual(doc["first_bad"], "c5")
        self.assertEqual(doc["status"], "converged")

    def test_all_good_no_regression(self) -> None:
        candidates = ["c1", "c2", "c3"]
        doc, _ = self._run(candidates, None)
        self.assertIsNone(doc["first_bad"])
        self.assertEqual(doc["status"], "no_regression")

    def test_single_candidate_bad(self) -> None:
        doc, probed = self._run(["only"], "only")
        self.assertEqual(doc["first_bad"], "only")
        self.assertEqual(probed, ["only"])

    def test_empty_range(self) -> None:
        recipe = make_recipe(self.dir)
        doc = run_bisect(
            self.backend,
            recipe,
            CONFIG,
            good="g",
            bad="b",
            repo_dir=self.dir,
            out_path=self.dir / "bisect.json",
            commit_provider=lambda g, b, r: [],
            verdict_runner=lambda sha: Verdict(sha=sha, exit_code=0),
        )
        self.assertEqual(doc["status"], "no_candidates")
        self.assertIsNone(doc["first_bad"])
        self.assertEqual(doc["tested_count"], 0)
        self.assertEqual(doc["total_candidates"], 0)

    def test_document_written_to_disk(self) -> None:
        candidates = ["c1", "c2", "c3", "c4"]
        out = self.dir / "out.json"
        doc, _ = self._run(candidates, "c3", out_name="out.json")
        on_disk = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(on_disk, doc)

    def test_document_shape_fields(self) -> None:
        candidates = ["c1", "c2", "c3"]
        doc, _ = self._run(candidates, "c2")
        # All blueprint §6 fields present with correct top-level types.
        self.assertEqual(doc["v"], 1)
        self.assertEqual(doc["recipe"], "demo")
        self.assertEqual(doc["good"], "g")
        self.assertEqual(doc["bad"], "b")
        self.assertEqual(doc["candidates"], candidates)
        self.assertEqual(doc["first_bad"], "c2")
        self.assertEqual(doc["status"], "converged")
        self.assertIsInstance(doc["verdicts"], list)
        # Each verdict carries the documented fields.
        for v in doc["verdicts"]:
            self.assertEqual(set(v), {"sha", "verdict", "exit_code", "step_failed", "duration_s"})
            self.assertIn(v["verdict"], ("good", "bad"))


class ResetAndIntegrationTest(unittest.TestCase):
    """Default path (owns a real base VM) against FakeBackend, git stubbed out."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        self.backend = FakeBackend()
        # Stub git so the default verdict runner never shells out.
        self._orig_checkout = bisect_mod._git_checkout
        bisect_mod._git_checkout = lambda sha, repo_dir: None

    def tearDown(self) -> None:
        bisect_mod._git_checkout = self._orig_checkout
        self._tmp.cleanup()

    def test_snapshot_apply_once_per_probe_and_first_bad(self) -> None:
        candidates = ["c1", "c2", "c3", "c4", "c5"]
        recipe = make_recipe(self.dir)
        vm_name = bisect_mod._bisect_vm_name(recipe)

        # Provision exec for the base build; "make test" verdict is seeded from a
        # regression marker the Fake filesystem carries from c4 onward.
        self.backend.on(vm_name, ["sh", "-c", "install deps"], ExecResult(0, "", ""))

        # The injected commit provider also records which sha is "active" so the
        # seeded `make test` handler can decide good/bad. copy_in writes a marker
        # keyed by sha (via the stubbed checkout we track the current sha here).
        state = {"sha": None}

        def commit_provider(good, bad, repo):
            return list(candidates)

        # Wrap _git_checkout to remember the active sha for this probe.
        bisect_mod._git_checkout = lambda sha, repo_dir: state.__setitem__("sha", sha)

        bad_from = candidates.index("c4")

        def make_test(fs, argv):
            # Regression present once the active sha is at/after c4.
            idx = candidates.index(state["sha"])
            return ExecResult(1, "", "regressed") if idx >= bad_from else ExecResult(0, "ok", "")

        self.backend.on(vm_name, ["make", "test"], make_test)

        # Count snapshot_apply calls (the per-candidate reset).
        apply_calls: list[str] = []
        orig_apply = self.backend.snapshot_apply

        def rec_apply(name, tag):
            apply_calls.append(tag)
            return orig_apply(name, tag)

        self.backend.snapshot_apply = rec_apply  # type: ignore[method-assign]

        out = self.dir / "bisect.json"
        doc = run_bisect(
            self.backend,
            recipe,
            CONFIG,
            good="g",
            bad="b",
            repo_dir=self.dir,
            out_path=out,
            commit_provider=commit_provider,
            # verdict_runner left as default → owns the base VM and resets.
        )

        self.assertEqual(doc["first_bad"], "c4")
        self.assertEqual(doc["status"], "converged")
        # snapshot_apply called exactly once per probed candidate, all to base-clean.
        self.assertEqual(len(apply_calls), doc["tested_count"])
        self.assertTrue(all(tag == BASE_SNAPSHOT_TAG for tag in apply_calls))
        # The base snapshot was taken once during the build.
        # The persistent VM is deleted after the run (keep defaults False).
        self.assertEqual(self.backend.status(vm_name).status, VmStatus.ABSENT)

    def test_base_snapshot_created_and_vm_kept(self) -> None:
        candidates = ["c1", "c2"]
        recipe = make_recipe(self.dir)
        vm_name = bisect_mod._bisect_vm_name(recipe)
        self.backend.on(vm_name, ["sh", "-c", "install deps"], ExecResult(0, "", ""))
        self.backend.on(vm_name, ["make", "test"], ExecResult(0, "ok", ""))

        run_bisect(
            self.backend,
            recipe,
            CONFIG,
            good="g",
            bad="b",
            repo_dir=self.dir,
            out_path=self.dir / "bisect.json",
            commit_provider=lambda g, b, r: list(candidates),
            keep=True,
        )
        # With keep=True the VM survives and still carries the base-clean snapshot.
        self.assertEqual(self.backend.status(vm_name).status, VmStatus.RUNNING)
        self.assertIn(BASE_SNAPSHOT_TAG, self.backend.snapshot_list(vm_name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
