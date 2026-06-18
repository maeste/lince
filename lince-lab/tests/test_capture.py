#!/usr/bin/env python3
"""Capture + template tests (blueprint §7, §3, §5).

Everything here runs against a scripted, in-process channel and a fake monotonic
clock — no PTY, no VM, no real sleeping, fully deterministic.

The capture cases exercise the two event-driven wait primitives:

* (a) needle appears after N ``output`` bursts → ``wait_for_substring`` returns
  the grid;
* (b) busy-then-quiet → ``wait_for_stable`` returns only after the silence
  window;
* (c) needle never appears → ``wait_for_substring`` raises ``CaptureTimeout``;
* (d) screen never settles → ``wait_for_stable`` raises ``CaptureTimeout``.

The template cases assert the policy-forced isolation fields and the net-cut
provision are present, and that an allowlist recipe emits an allow rule instead.

Run with:
    python3 lince-lab/tests/test_capture.py
"""

import json
import pathlib
import sys
import unittest

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab import capture as capture_mod  # noqa: E402
from lince_lab.backend import CaptureChannel  # noqa: E402
from lince_lab.capture import Capture, CaptureTimeout, Grid  # noqa: E402
from lince_lab.templates import (  # noqa: E402
    NET_ALLOW_MARKER,
    NET_CUT_MARKER,
    build_template,
)


class FakeClock:
    """A monotonic clock advanced explicitly by the scripted channel."""

    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _snapshot_event(text: str, cols: int = 80, rows: int = 24) -> dict:
    return {"type": "snapshot", "data": {"cols": cols, "rows": rows, "text": text, "seq": ""}}


def _output_event(payload: str = "x") -> dict:
    return {"type": "output", "data": payload}


class ScriptedChannel(CaptureChannel):
    """Deterministic channel: replies to ``takeSnapshot`` and replays a script.

    The channel models a terminal whose *current* grid text changes over time.
    ``script`` is a list of ``(advance_s, event)`` steps consumed by
    ``read_line``; ``advance_s`` moves the fake clock forward *before* the event
    is returned, so silence windows and overall deadlines are exercised exactly.

    A ``("set_text", new_text)`` control step updates the grid that subsequent
    ``takeSnapshot`` commands report, modelling output that mutates the screen.
    When the script is exhausted, ``read_line`` advances the clock to (at least)
    the requested deadline and returns ``None`` — i.e. permanent silence.
    """

    def __init__(self, clock: FakeClock, script: list, initial_text: str = "") -> None:
        self._clock = clock
        self._script = list(script)
        self._text = initial_text
        self.sent: list[dict] = []
        self.closed = False

    def send_line(self, obj: dict) -> None:
        self.sent.append(dict(obj))

    def read_line(self, deadline: float):
        while self._script:
            advance, event = self._script.pop(0)
            self._clock.advance(advance)
            if isinstance(event, tuple) and event and event[0] == "set_text":
                self._text = event[1]
                continue
            return event
        # Exhausted: jump to the deadline (permanent silence) and report nothing.
        if self._clock.monotonic() < deadline:
            self._clock.t = deadline
        return None

    def current_snapshot(self) -> dict:
        return _snapshot_event(self._text)

    def close(self) -> None:
        self.closed = True


class _SnapshotAnsweringChannel(ScriptedChannel):
    """ScriptedChannel that answers ``takeSnapshot`` from its current text.

    Capture's snapshot helpers send ``{"type":"takeSnapshot"}`` and then read
    until a ``snapshot`` event. We satisfy that by pushing the current grid to
    the FRONT of the script whenever a ``takeSnapshot`` command is sent.
    """

    def send_line(self, obj: dict) -> None:
        super().send_line(obj)
        if obj.get("type") == "takeSnapshot":
            # Answer immediately (no clock advance) with the current grid.
            self._script.insert(0, (0.0, self.current_snapshot()))


class CaptureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        # Drive Capture's deadlines off the fake clock — keeps tests instant and
        # deterministic, and proves the loops are deadline-driven not sleep-driven.
        self._orig_monotonic = capture_mod.time.monotonic
        capture_mod.time.monotonic = self.clock.monotonic

    def tearDown(self) -> None:
        capture_mod.time.monotonic = self._orig_monotonic

    # ── (a) needle appears after N output bursts ─────────────────────────────
    def test_wait_for_substring_returns_when_needle_appears(self) -> None:
        # Three output bursts; the third reveals the needle in the grid.
        script = [
            (0.1, _output_event()),
            (0.1, _output_event()),
            (0.1, ("set_text", "loading...\nReady: continue?")),
            (0.1, _output_event()),
        ]
        ch = _SnapshotAnsweringChannel(self.clock, script, initial_text="booting\n")
        cap = Capture(ch, cols=80, rows=24)
        grid = cap.wait_for_substring("Ready: continue?", timeout_s=10.0)
        self.assertIsInstance(grid, Grid)
        self.assertTrue(grid.contains("Ready: continue?"))

    # ── (b) busy-then-quiet → stable only after the silence window ───────────
    def test_wait_for_stable_returns_after_silence(self) -> None:
        # Two output bursts (busy), then the script is exhausted (quiet).
        script = [
            (0.05, ("set_text", "frame-1")),
            (0.05, _output_event()),
            (0.05, ("set_text", "frame-2")),
            (0.05, _output_event()),
        ]
        ch = _SnapshotAnsweringChannel(self.clock, script, initial_text="frame-0")
        cap = Capture(ch, cols=80, rows=24)
        t_start = self.clock.monotonic()
        grid = cap.wait_for_stable(debounce_ms=150, timeout_s=10.0)
        # It settled on the last rendered frame, and only after activity ceased.
        self.assertEqual(grid.text, "frame-2")
        # The busy bursts advanced the clock before silence was declared.
        self.assertGreater(self.clock.monotonic(), t_start)

    # ── (c) needle never appears → CaptureTimeout ────────────────────────────
    def test_wait_for_substring_times_out(self) -> None:
        # Output keeps coming but the needle is never rendered; clock crosses the
        # deadline, so the wait must raise.
        script = [(0.3, _output_event()) for _ in range(20)]
        ch = _SnapshotAnsweringChannel(self.clock, script, initial_text="nothing here\n")
        cap = Capture(ch, cols=80, rows=24)
        with self.assertRaises(CaptureTimeout):
            cap.wait_for_substring("NEVER", timeout_s=1.0)

    # ── (d) screen never settles → CaptureTimeout ────────────────────────────
    def test_wait_for_stable_times_out_when_never_quiet(self) -> None:
        # An output burst arrives within every debounce window, forever resetting
        # the silence window until the overall budget is spent.
        script = [(0.05, _output_event()) for _ in range(200)]
        ch = _SnapshotAnsweringChannel(self.clock, script, initial_text="busy\n")
        cap = Capture(ch, cols=80, rows=24)
        with self.assertRaises(CaptureTimeout):
            cap.wait_for_stable(debounce_ms=150, timeout_s=1.0)

    # ── fire-and-exit: output seen, then EOF before any snapshot ─────────────
    def test_wait_for_substring_matches_output_then_eof(self) -> None:
        # Models `echo MARKER` under ht v0.4.0: ht emits one object-shaped output
        # burst carrying the text, then the program exits and the channel goes to
        # EOF — never answering a takeSnapshot. The needle must still match off the
        # accumulated output, not raise a spurious "no snapshot" timeout.
        script = [(0.1, {"type": "output", "data": {"seq": "lince-capture-ok\r\n"}})]
        # A plain ScriptedChannel never answers takeSnapshot, so every _try_snapshot
        # returns None — exactly the "grid already torn down" situation.
        ch = ScriptedChannel(self.clock, script, initial_text="")
        cap = Capture(ch, cols=80, rows=24)
        grid = cap.wait_for_substring("lince-capture-ok", timeout_s=10.0)
        self.assertTrue(grid.contains("lince-capture-ok"))

    def test_wait_for_substring_eof_without_match_raises(self) -> None:
        # Output that never carries the needle, then EOF → genuine timeout.
        script = [(0.1, {"type": "output", "data": {"seq": "something-else\r\n"}})]
        ch = ScriptedChannel(self.clock, script, initial_text="")
        cap = Capture(ch, cols=80, rows=24)
        with self.assertRaises(CaptureTimeout):
            cap.wait_for_substring("lince-capture-ok", timeout_s=1.0)

    # ── snapshot() basic round-trip ──────────────────────────────────────────
    def test_snapshot_returns_current_grid(self) -> None:
        ch = _SnapshotAnsweringChannel(self.clock, [], initial_text="hello\nworld")
        cap = Capture(ch, cols=80, rows=24)
        grid = cap.snapshot()
        self.assertEqual(grid.text, "hello\nworld")
        self.assertTrue(grid.contains("world"))

    def test_send_keys_and_input_are_framed(self) -> None:
        ch = _SnapshotAnsweringChannel(self.clock, [], initial_text="")
        cap = Capture(ch, cols=80, rows=24)
        cap.send_keys(["Down", "Enter"])
        cap.input("ls\r")
        cap.resize(100, 40)
        self.assertEqual(ch.sent[0], {"type": "sendKeys", "keys": ["Down", "Enter"]})
        self.assertEqual(ch.sent[1], {"type": "input", "payload": "ls\r"})
        self.assertEqual(ch.sent[2], {"type": "resize", "cols": 100, "rows": 40})
        self.assertEqual((cap.cols, cap.rows), (100, 40))


class TemplateTestCase(unittest.TestCase):
    def _config(self) -> dict:
        return {
            "vm": {"cpus": 2, "memory": "2GiB", "disk": "20GiB"},
            "images": {
                "fedora": {
                    "location": "https://example/Fedora-Cloud.qcow2",
                    "arch": "x86_64",
                    "digest": "sha256:deadbeef",
                }
            },
        }

    def test_policy_forced_fields_and_no_boot_egress(self) -> None:
        text = build_template(self._config(), {"image": "fedora"})
        tmpl = json.loads(text)  # JSON is valid YAML; round-trips
        # Policy-forced isolation invariants.
        self.assertIs(tmpl["plain"], True)
        self.assertEqual(tmpl["mounts"], [])
        self.assertIs(tmpl["ssh"]["loadDotSSHPubKeys"], False)
        # Resources resolved from config vm defaults.
        self.assertEqual(tmpl["cpus"], 2)
        self.assertEqual(tmpl["memory"], "2GiB")
        self.assertEqual(tmpl["disk"], "20GiB")
        # Pinned image location + digest from the config allowlist.
        self.assertEqual(tmpl["images"][0]["location"], "https://example/Fedora-Cloud.qcow2")
        self.assertEqual(tmpl["images"][0]["digest"], "sha256:deadbeef")
        # The VM boots networked: NO boot egress provision is baked into the
        # template (egress is restricted at runtime, after provisioning).
        self.assertEqual([p for p in tmpl.get("provision", []) if p.get("mode") == "boot"], [])
        self.assertNotIn(NET_CUT_MARKER, text)
        self.assertNotIn(NET_ALLOW_MARKER, text)
        self.assertNotIn("policy drop", text)

    def test_resource_override_from_needs(self) -> None:
        needs = {"image": "fedora", "cpus": 4, "memory": "8GiB", "disk": "40GiB"}
        tmpl = json.loads(build_template(self._config(), needs))
        self.assertEqual(tmpl["cpus"], 4)
        self.assertEqual(tmpl["memory"], "8GiB")
        self.assertEqual(tmpl["disk"], "40GiB")

    def test_unknown_image_rejected(self) -> None:
        from lince_lab.errors import DataError

        with self.assertRaises(DataError):
            build_template(self._config(), {"image": "no-such-image"})


class RenderTestCase(unittest.TestCase):
    """#256 pixel-PNG render layer over the canonical text grid (ADR-10).

    Pillow is an OPTIONAL dependency: when present, the renderer emits a valid PNG
    (magic-byte checked); when absent, the renderer refuses rather than faking an
    image (the CLI falls back to a .txt artifact). Both paths are asserted.
    """

    def test_grid_text_to_png_is_a_valid_png_when_pillow_present(self) -> None:
        from lince_lab import render

        if not render.PIL_AVAILABLE:
            self.skipTest("Pillow not installed; PNG path covered by the .txt fallback test")
        png = render.grid_text_to_png("New Agent\n  claude\n  codex\n", 80, 24)
        # PNG magic number — proves a real, decodable image header.
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertGreater(len(png), 8)

    def test_render_refuses_without_pillow_never_fakes_a_png(self) -> None:
        # When Pillow is unavailable the renderer raises (no fake PNG ever). We
        # simulate absence by flipping the module flag so the honest-fallback
        # contract is exercised even on a host that has Pillow installed.
        from lince_lab import render
        from lince_lab.errors import DataError

        orig = render.PIL_AVAILABLE
        render.PIL_AVAILABLE = False
        try:
            with self.assertRaises(DataError):
                render.grid_text_to_png("x", 80, 24)
        finally:
            render.PIL_AVAILABLE = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
