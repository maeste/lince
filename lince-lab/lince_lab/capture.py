"""Terminal-capture / oracle API (blueprint §7).

:class:`Capture` wraps a :class:`~lince_lab.backend.CaptureChannel` (the duplex
line transport to ``ht`` inside the VM, or a scripted in-process channel under
test) and exposes the deterministic primitives the recipe runner and the
``watch`` CLI verbs need: ``send_keys``, ``input``, ``snapshot``,
``wait_for_substring``, ``wait_for_stable``, ``resize``, ``close``.

The two wait primitives are **event-driven** — they block on
:meth:`CaptureChannel.read_line` against a :func:`time.monotonic` deadline and
react only when the terminal actually produces ``output`` or ``snapshot``
events. There is deliberately **no** :func:`time.sleep` in any wait loop: a busy
screen never reaches the deadline, a quiet one returns the instant the silence
window elapses. On deadline they raise :class:`CaptureTimeout`
(``DATA_ERROR`` / exit 65).

Wire shapes (see ``claudedocs/lince-lab/capture.md``):

* Commands → channel: ``{"type": "sendKeys", "keys": [...]}``,
  ``{"type": "input", "payload": "..."}``, ``{"type": "takeSnapshot"}``,
  ``{"type": "resize", "cols": C, "rows": R}``.
* Events ← channel: ``{"type": "output", "data": "..."}`` (a byte burst from the
  TUI) and ``{"type": "snapshot", "data": {"cols", "rows", "text", "seq"}}``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from lince_lab.backend import CaptureChannel
from lince_lab.errors import DataError


class CaptureTimeout(DataError):
    """A wait primitive hit its deadline before the condition was met.

    Inherits :class:`~lince_lab.errors.DataError` so it carries exit code 65
    (``DATA_ERROR``) — a capture that never reaches its expected state is a
    recipe/run data failure, not a crash.
    """


@dataclass
class Grid:
    """A rendered terminal grid — the assertion surface.

    ``text`` is the grid as a single string, one line per terminal row (exactly
    the ``ht`` ``snapshot.data.text`` field).
    """

    cols: int
    rows: int
    text: str

    def contains(self, s: str) -> bool:
        """Return ``True`` iff ``s`` appears anywhere in the rendered grid."""
        return s in self.text


def _grid_from_event(data: dict, fallback_cols: int, fallback_rows: int) -> Grid:
    """Build a :class:`Grid` from a ``snapshot`` event's ``data`` payload."""
    text = data.get("text", "")
    if not isinstance(text, str):
        raise DataError(f"snapshot 'text' must be a string, got {type(text).__name__}")
    cols = data.get("cols", fallback_cols)
    rows = data.get("rows", fallback_rows)
    return Grid(cols=int(cols), rows=int(rows), text=text)


class Capture:
    """Drives a terminal-capture process over a :class:`CaptureChannel`."""

    def __init__(self, channel: CaptureChannel, cols: int, rows: int) -> None:
        self._channel = channel
        self.cols = cols
        self.rows = rows

    # ── command surface ──────────────────────────────────────────────────────
    def send_keys(self, keys: list[str]) -> None:
        """Inject named keys (``Enter``, ``^x``, ``Down`` ...) in order."""
        self._channel.send_line({"type": "sendKeys", "keys": list(keys)})

    def input(self, payload: str) -> None:
        """Inject raw bytes (no key-name parsing), e.g. ``"ls\\r"``."""
        self._channel.send_line({"type": "input", "payload": payload})

    def resize(self, cols: int, rows: int) -> None:
        """Resize the captured grid and remember the new dimensions."""
        self.cols = cols
        self.rows = rows
        self._channel.send_line({"type": "resize", "cols": cols, "rows": rows})

    def close(self) -> None:
        """Close the underlying channel."""
        self._channel.close()

    # ── snapshot ─────────────────────────────────────────────────────────────
    def snapshot(self, timeout_s: float = 5.0) -> Grid:
        """Request and return the current text grid.

        Sends ``takeSnapshot`` and consumes channel events until the matching
        ``snapshot`` event arrives, ignoring any interleaved ``output`` bursts.
        Raises :class:`CaptureTimeout` if no snapshot arrives within
        ``timeout_s``.
        """
        return self._take_snapshot(time.monotonic() + timeout_s)

    def _take_snapshot(self, deadline: float) -> Grid:
        """Send ``takeSnapshot`` and read until the ``snapshot`` event (no sleep)."""
        self._channel.send_line({"type": "takeSnapshot"})
        while True:
            event = self._channel.read_line(deadline)
            if event is None:
                raise CaptureTimeout("timed out waiting for terminal snapshot")
            if event.get("type") == "snapshot":
                data = event.get("data") or {}
                return _grid_from_event(data, self.cols, self.rows)
            # Any other event (e.g. an interleaved 'output') is consumed and the
            # loop keeps reading until the snapshot lands. The deadline still
            # bounds the wait, so this cannot spin forever.

    # ── deterministic waits (event-driven, NO time.sleep) ────────────────────
    def wait_for_substring(self, needle: str, timeout_s: float) -> Grid:
        """Block until ``needle`` appears in the grid; return that :class:`Grid`.

        Event-driven: blocks on :meth:`CaptureChannel.read_line` against a
        monotonic deadline. On every ``output`` (or ``snapshot``) event it
        re-snapshots the grid and checks for ``needle``. Raises
        :class:`CaptureTimeout` on the deadline. No :func:`time.sleep`.
        """
        deadline = time.monotonic() + timeout_s
        # Check the current grid first — the needle may already be on screen.
        grid = self._take_snapshot(deadline)
        if grid.contains(needle):
            return grid
        while True:
            event = self._channel.read_line(deadline)
            if event is None:
                raise CaptureTimeout(f"timed out waiting for substring: {needle!r}")
            etype = event.get("type")
            if etype == "snapshot":
                data = event.get("data") or {}
                grid = _grid_from_event(data, self.cols, self.rows)
                if grid.contains(needle):
                    return grid
            elif etype == "output":
                grid = self._take_snapshot(deadline)
                if grid.contains(needle):
                    return grid
            # Other event types are ignored; the deadline still bounds the loop.

    def wait_for_stable(self, debounce_ms: int, timeout_s: float) -> Grid:
        """Block until the grid stops changing for ``debounce_ms``; return it.

        "Stable" means *event silence*: the latest snapshot is unchanged and no
        ``output`` arrives within the ``debounce_ms`` window. The window is a
        deadline on a blocking :meth:`read_line`, not a :func:`time.sleep` — it
        returns the instant an ``output`` arrives (resetting the window) and
        settles the instant the window elapses with no change. Bounded overall
        by ``timeout_s``; raises :class:`CaptureTimeout` if it never settles.
        """
        debounce_s = debounce_ms / 1000.0
        overall_deadline = time.monotonic() + timeout_s
        grid = self._take_snapshot(overall_deadline)
        while True:
            # If the overall budget is spent and we still have not seen a full
            # quiet window, the terminal never settled.
            if time.monotonic() >= overall_deadline:
                raise CaptureTimeout("timed out waiting for terminal to settle")
            # Read for at most one debounce window, never past the overall budget.
            window_deadline = min(time.monotonic() + debounce_s, overall_deadline)
            event = self._channel.read_line(window_deadline)
            if event is None:
                if window_deadline >= overall_deadline:
                    # The window we just waited was truncated by the overall
                    # deadline, so this is a timeout, not a settled screen.
                    raise CaptureTimeout("timed out waiting for terminal to settle")
                # Silence for a full debounce window → grid is stable.
                return grid
            etype = event.get("type")
            if etype == "snapshot":
                data = event.get("data") or {}
                grid = _grid_from_event(data, self.cols, self.rows)
                # An update restarts the silence window (loop).
            elif etype == "output":
                # Activity: re-snapshot and restart the window.
                grid = self._take_snapshot(overall_deadline)
            # Any other event also restarts the window via the loop.
