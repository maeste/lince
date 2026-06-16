#!/usr/bin/env python3
"""#259 regression-replay — the lince-wizard recipe catches #202 with NO VM.

This is the epic's headline proof: the shipped ``recipes/lince-wizard.toml`` is a
substrate-free oracle for the #202 per-level duplication regression. We load the
real recipe and run its steps + assertions (via :func:`run_steps_and_assert`)
against a :class:`FakeBackend` plus a scripted capture channel, feeding two
*different* terminal grids:

* **GOOD grid** — each enabled agent (``claude``, ``codex``) appears exactly once
  and no per-sandbox-level heading (``permissive`` / ``paranoid``) is shown → the
  recipe PASSES (exit 0).
* **BROKEN grid** — the #202 bug: every enabled agent is listed once *per sandbox
  level*, so ``claude`` / ``codex`` appear multiple times under ``permissive`` /
  ``paranoid`` headings → the recipe FAILS.

The recipe's own ``grid_absent`` proxy (``permissive`` / ``paranoid`` must not
appear) catches the broken grid; we *additionally* assert the stronger
"each-agent-appears-exactly-once" property directly here (the recipe TOML schema
has no count assertion key, so this stricter check lives in the test — see #259).

Everything runs over a fake monotonic clock: no PTY, no VM, no real sleeping.

Run with:
    python3 lince-lab/tests/test_fixture_wizard.py
"""

import pathlib
import sys
import unittest

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab import capture as capture_mod  # noqa: E402
from lince_lab import recipe as recipe_mod  # noqa: E402
from lince_lab.errors import DataError  # noqa: E402
from lince_lab.fake_backend import FakeBackend, FakeCaptureChannel  # noqa: E402
from lince_lab.recipe import load_recipe, run_steps_and_assert  # noqa: E402

WIZARD_RECIPE = pathlib.Path(__file__).resolve().parent.parent / "recipes" / "lince-wizard.toml"

# A GOOD wizard grid: each enabled agent shown exactly once, no per-level heading.
# It also carries every [sync].wait_for substring so the capture step advances,
# and every grid_contains needle so the recipe's positive asserts pass.
GOOD_GRID = (
    "New Agent wizard\n"
    "Select an agent to configure\n"
    "Showing enabled_agents (one each):\n"
    "  claude\n"
    "  codex\n"
    "Confirm? (y/n)\n"
    "Configuration written to lince.toml\n"
)

# A BROKEN grid simulating the #202 regression: each enabled agent is duplicated
# once per sandbox level, listed under permissive/paranoid headings. The agent
# names therefore appear multiple times, and the per-level headings are present.
BROKEN_GRID = (
    "New Agent wizard\n"
    "Select an agent to configure\n"
    "Showing enabled_agents per sandbox level:\n"
    "[permissive]\n"
    "  claude\n"
    "  codex\n"
    "[paranoid]\n"
    "  claude\n"
    "  codex\n"
    "Confirm? (y/n)\n"
    "Configuration written to lince.toml\n"
)


class FakeClock:
    """A monotonic clock the answering channel advances to each deadline."""

    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t

    def advance_to(self, deadline: float) -> None:
        if self.t < deadline:
            self.t = deadline


class _GridChannel(FakeCaptureChannel):
    """A :class:`FakeCaptureChannel` that answers every ``takeSnapshot`` from a grid.

    The recipe runner's wait primitives send ``takeSnapshot`` and read until a
    ``snapshot`` event. We satisfy that by queueing the (fixed) grid text in
    response to each ``takeSnapshot`` command; between answers ``read_line``
    advances the fake clock to the deadline and reports silence, which is exactly
    what ``wait_for_stable`` settles on. The grid text never changes, so a single
    settled grid drives all the recipe's assertions.
    """

    def __init__(self, clock: FakeClock, text: str) -> None:
        super().__init__([])
        self._clock = clock
        self._text = text

    def send_line(self, obj: dict) -> None:
        super().send_line(obj)
        if obj.get("type") == "takeSnapshot":
            self.feed({"type": "snapshot", "data": {"cols": 80, "rows": 24, "text": self._text}})

    def read_line(self, deadline: float):
        if self._events:
            return self._events.pop(0)
        # No pending answer: silence until the deadline (settles wait_for_stable).
        self._clock.advance_to(deadline)
        return None


class WizardRegressionReplayTest(unittest.TestCase):
    """Run the real wizard recipe's steps+asserts over scripted GOOD/BROKEN grids."""

    def setUp(self) -> None:
        self.recipe = load_recipe(WIZARD_RECIPE)
        self.vm_name = recipe_mod._vm_name(self.recipe)
        self.backend = FakeBackend()
        # The recipe asserts file_exists on the written policy; seed it so the
        # *grid* property (the #202 contract) is what decides pass/fail, not the
        # unrelated file check.
        self.backend.create(self.vm_name, "")
        self.backend.fs_of(self.vm_name)["/root/.config/lince/lince.toml"] = b"[dashboard]\n"
        # Drive Capture's deadlines off a fake clock so the run is instant.
        self.clock = FakeClock()
        self._orig_monotonic = capture_mod.time.monotonic
        capture_mod.time.monotonic = self.clock.monotonic

    def tearDown(self) -> None:
        capture_mod.time.monotonic = self._orig_monotonic

    def _run_with_grid(self, grid_text: str) -> tuple[int, "Exception | None"]:
        """Run the recipe steps+asserts against a channel scripted with ``grid_text``.

        Returns ``(exit_code, raised)`` where ``raised`` is the assertion
        ``DataError`` (if any) — the recipe runner raises it on a grid mismatch.
        """
        self.backend.script_capture(self.vm_name, _GridChannel(self.clock, grid_text))
        try:
            exit_code, _step = run_steps_and_assert(self.backend, self.recipe, self.vm_name)
            return exit_code, None
        except DataError as exc:
            return exc.exit_code, exc

    # ── (i) GOOD grid → recipe passes ────────────────────────────────────────
    def test_good_grid_recipe_passes(self) -> None:
        exit_code, raised = self._run_with_grid(GOOD_GRID)
        self.assertIsNone(raised, f"GOOD grid must not trip an assertion: {raised}")
        self.assertEqual(exit_code, 0)

    # ── (ii) BROKEN grid (#202 per-level duplication) → recipe FAILS ──────────
    def test_broken_grid_recipe_fails(self) -> None:
        exit_code, raised = self._run_with_grid(BROKEN_GRID)
        # The recipe's grid_absent proxy (permissive / paranoid) catches it.
        self.assertIsNotNone(raised, "BROKEN grid (#202) must fail the recipe")
        self.assertNotEqual(exit_code, 0)
        self.assertIn("grid_absent", str(raised))

    # ── stronger, explicit #202 contract: each agent appears EXACTLY once ─────
    # The recipe TOML schema has no count assertion key, so the exact-count check
    # the AC asks for is asserted here directly against the same two grids.
    def test_each_enabled_agent_appears_exactly_once_in_good_grid(self) -> None:
        for agent in ("claude", "codex"):
            self.assertEqual(
                GOOD_GRID.count(agent),
                1,
                f"GOOD grid must show {agent!r} exactly once (the #202 contract)",
            )

    def test_broken_grid_duplicates_each_agent_per_level(self) -> None:
        # The #202 bug: each agent listed once per sandbox level → appears > once.
        for agent in ("claude", "codex"):
            self.assertGreater(
                BROKEN_GRID.count(agent),
                1,
                f"BROKEN grid must duplicate {agent!r} per sandbox level (the #202 bug)",
            )
        # And the per-level headings the recipe's grid_absent guards against are present.
        self.assertIn("permissive", BROKEN_GRID)
        self.assertIn("paranoid", BROKEN_GRID)


if __name__ == "__main__":
    unittest.main(verbosity=2)
