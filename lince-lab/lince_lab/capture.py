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

Wire shapes (ht v0.4.0; see ``claudedocs/lince-lab/capture.md``):

* Commands → channel: ``{"type": "sendKeys", "keys": [...]}``,
  ``{"type": "input", "payload": "..."}``, ``{"type": "takeSnapshot"}``,
  ``{"type": "resize", "cols": C, "rows": R}``.
* Events ← channel: ``{"type": "output", "data": {"seq": "..."}}`` (a byte burst
  from the TUI — v0.4.0 wraps it in an object; older/scripted channels pass a
  bare string, both are accepted), ``{"type": "snapshot", "data": {"cols",
  "rows", "text", "seq"}}``, and ``{"type": "init", "data": {...snapshot...}}``
  (emitted once at startup, carrying the initial grid).

Robustness: a program that prints then exits (``echo``) makes ht close its
streams almost immediately, so a snapshot request can race the EOF. The wait
primitives therefore (a) never treat a single missed snapshot as fatal, (b)
accumulate ``output`` bursts and match the needle against them too, and (c) do a
final match on EOF before giving up — and a genuine timeout carries the
channel's :meth:`~lince_lab.backend.CaptureChannel.diagnostics` (ht argv, exit
status, stderr/stdout tails) so the failure explains itself.
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
    """Build a :class:`Grid` from a ``snapshot``/``init`` event's ``data`` payload."""
    text = data.get("text", "")
    if not isinstance(text, str):
        raise DataError(f"snapshot 'text' must be a string, got {type(text).__name__}")
    cols = data.get("cols", fallback_cols)
    rows = data.get("rows", fallback_rows)
    return Grid(cols=int(cols), rows=int(rows), text=text)


def _output_text(event: dict) -> str:
    """Extract the printable text of an ``output`` event.

    ht v0.4.0 wraps the byte burst in ``{"data": {"seq": "..."}}``; older/scripted
    channels pass a bare string in ``data``. Both are accepted (anything else
    yields the empty string), so substring matching works across versions.
    """
    data = event.get("data")
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        seq = data.get("seq", "")
        return seq if isinstance(seq, str) else ""
    return ""


# Event types that carry a renderable grid in their ``data`` payload.
_SNAPSHOTISH = ("snapshot", "init")


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

    # ── diagnostics ──────────────────────────────────────────────────────────
    def _diag(self) -> str:
        """Append the channel's diagnostics blob to a timeout message, if any."""
        text = self._channel.diagnostics()
        return f"\n--- capture diagnostics ---\n{text}" if text else ""

    # ── snapshot ─────────────────────────────────────────────────────────────
    def snapshot(self, timeout_s: float = 5.0) -> Grid:
        """Request and return the current text grid.

        Sends ``takeSnapshot`` and consumes channel events until the matching
        ``snapshot`` (or ``init``) event arrives, ignoring any interleaved
        ``output`` bursts. Raises :class:`CaptureTimeout` if no snapshot arrives
        within ``timeout_s`` (with channel diagnostics attached).
        """
        grid = self._try_snapshot(time.monotonic() + timeout_s)
        if grid is None:
            raise CaptureTimeout("timed out waiting for terminal snapshot" + self._diag())
        return grid

    def _request_snapshot(self) -> None:
        """Send ``takeSnapshot`` to prompt a grid, swallowing a closed-channel error.

        Used by the unified :meth:`wait_for_substring` loop, which reads the
        resulting ``snapshot`` event itself (rather than a nested read loop that
        would discard the interleaved ``output`` bursts we need to accumulate)."""
        try:
            self._channel.send_line({"type": "takeSnapshot"})
        except Exception:  # noqa: BLE001 — a closed channel just means "no grid"
            pass

    def _try_snapshot(self, deadline: float) -> Grid | None:
        """Send ``takeSnapshot`` and read until a grid event, or ``None`` on EOF.

        Unlike a hard snapshot, this NEVER raises: a ``None`` return means the
        channel went silent / the capture process exited before answering, which
        the wait primitives treat as "try the accumulated output / give up" rather
        than an immediate failure. No :func:`time.sleep`.

        NOTE: this consumes (and ignores) any non-snapshot events read while
        waiting for the grid, so it is used only by :meth:`snapshot` and
        :meth:`wait_for_stable`, where a swallowed ``output`` only means "activity".
        :meth:`wait_for_substring` must NOT use it — it needs every ``output``.
        """
        self._request_snapshot()
        while True:
            event = self._channel.read_line(deadline)
            if event is None:
                return None
            if event.get("type") in _SNAPSHOTISH:
                return _grid_from_event(event.get("data") or {}, self.cols, self.rows)
            # Any other event (e.g. an interleaved 'output') is consumed and the
            # loop keeps reading until the snapshot lands. The deadline still
            # bounds the wait, so this cannot spin forever.

    # ── deterministic waits (event-driven, NO time.sleep) ────────────────────
    def wait_for_substring(self, needle: str, timeout_s: float) -> Grid:
        """Block until ``needle`` appears on screen; return the matching :class:`Grid`.

        Event-driven: blocks on :meth:`CaptureChannel.read_line` against a
        monotonic deadline. The needle is matched against BOTH the rendered grid
        (``snapshot``/``init`` events, re-snapshotted on activity) AND the raw
        ``output`` stream — so a program that prints then exits still matches even
        though ht tears its grid down on exit. On a clean EOF a final match is
        attempted before raising :class:`CaptureTimeout` (with diagnostics). No
        :func:`time.sleep`.
        """
        deadline = time.monotonic() + timeout_s
        output_acc = ""
        last_grid: Grid | None = None
        # Prompt an initial grid (its snapshot event is read by THIS loop, so any
        # output interleaved before it is accumulated, not discarded).
        self._request_snapshot()
        while True:
            event = self._channel.read_line(deadline)
            if event is None:
                # EOF or deadline. Match against everything we accumulated before
                # declaring failure — the program may have printed then exited.
                if last_grid is not None and last_grid.contains(needle):
                    return last_grid
                if needle in output_acc:
                    return last_grid or Grid(self.cols, self.rows, output_acc)
                raise CaptureTimeout(f"timed out waiting for substring: {needle!r}" + self._diag())
            etype = event.get("type")
            if etype in _SNAPSHOTISH:
                last_grid = _grid_from_event(event.get("data") or {}, self.cols, self.rows)
                if last_grid.contains(needle):
                    return last_grid
            elif etype == "output":
                output_acc += _output_text(event)
                if needle in output_acc:
                    # The text appeared in the stream. Prefer a settled grid if we
                    # already have one carrying it; else synthesize from the output
                    # (the program may have exited and torn its grid down).
                    if last_grid is not None and last_grid.contains(needle):
                        return last_grid
                    return Grid(self.cols, self.rows, output_acc)
                # Activity but no match yet: prompt a fresh grid; its snapshot event
                # arrives on a later iteration of THIS loop.
                self._request_snapshot()
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
        grid = self._try_snapshot(overall_deadline)
        if grid is None:
            raise CaptureTimeout("timed out waiting for terminal snapshot" + self._diag())
        while True:
            # If the overall budget is spent and we still have not seen a full
            # quiet window, the terminal never settled.
            if time.monotonic() >= overall_deadline:
                raise CaptureTimeout("timed out waiting for terminal to settle" + self._diag())
            # Read for at most one debounce window, never past the overall budget.
            window_deadline = min(time.monotonic() + debounce_s, overall_deadline)
            event = self._channel.read_line(window_deadline)
            if event is None:
                if window_deadline >= overall_deadline:
                    # The window we just waited was truncated by the overall
                    # deadline, so this is a timeout, not a settled screen.
                    raise CaptureTimeout("timed out waiting for terminal to settle" + self._diag())
                # Silence for a full debounce window → grid is stable.
                return grid
            etype = event.get("type")
            if etype in _SNAPSHOTISH:
                grid = _grid_from_event(event.get("data") or {}, self.cols, self.rows)
                # An update restarts the silence window (loop).
            elif etype == "output":
                # Activity: re-snapshot and restart the window. If the program
                # exited mid-window the snapshot is gone — keep the last grid and
                # let the next silent window settle it.
                fresh = self._try_snapshot(overall_deadline)
                if fresh is not None:
                    grid = fresh
            # Any other event also restarts the window via the loop.
