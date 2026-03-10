"""Terminal multiplexer pane capture for tmux and zellij."""

from __future__ import annotations

import os
import subprocess
import tempfile

DIRECTIONAL_TARGETS = {"left", "right", "up", "down"}
CYCLE_TARGETS = {"next", "previous"}
VALID_ZELLIJ_TARGETS = DIRECTIONAL_TARGETS | CYCLE_TARGETS

OPPOSITE_DIRECTION = {
    "left": "right",
    "right": "left",
    "up": "down",
    "down": "up",
    "next": "previous",
    "previous": "next",
}


def detect_multiplexer() -> str:
    """Detect active terminal multiplexer from environment."""
    if os.environ.get("ZELLIJ") or os.environ.get("ZELLIJ_SESSION_NAME"):
        return "zellij"
    if os.environ.get("TMUX"):
        return "tmux"
    raise RuntimeError(
        "Not running inside tmux or Zellij. "
        "Use --pane only from within a terminal multiplexer session."
    )


def capture_tmux_pane(target_pane: str = "") -> str:
    """Capture content of a tmux pane using `tmux capture-pane -p`."""
    cmd = ["tmux", "capture-pane", "-p"]
    if target_pane:
        cmd.extend(["-t", target_pane])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"tmux capture-pane failed: {result.stderr.strip()}")
    return result.stdout


def _zellij_focus(direction: str) -> None:
    """Focus a zellij pane by direction."""
    if direction in DIRECTIONAL_TARGETS:
        subprocess.run(["zellij", "action", "move-focus", direction], check=True, timeout=5)
    elif direction in CYCLE_TARGETS:
        subprocess.run(["zellij", "action", f"focus-{direction}-pane"], check=True, timeout=5)


def capture_zellij_pane(target_pane: str = "") -> str:
    """Capture content of a zellij pane using `zellij action dump-screen`.

    Args:
        target_pane: Directional target (left, right, up, down, next, previous).
            If empty, captures the current pane.
    """
    if target_pane and target_pane not in VALID_ZELLIJ_TARGETS:
        valid = ", ".join(sorted(VALID_ZELLIJ_TARGETS))
        raise ValueError(f"Invalid zellij pane target '{target_pane}'. Valid values: {valid}")

    with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if target_pane:
            # Focus target pane, dump its screen, focus back
            _zellij_focus(target_pane)

        cmd = ["zellij", "action", "dump-screen", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if target_pane:
            _zellij_focus(OPPOSITE_DIRECTION[target_pane])

        if result.returncode != 0:
            raise RuntimeError(f"zellij dump-screen failed: {result.stderr.strip()}")
        with open(tmp_path, "r") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def capture_pane(backend: str = "auto", target_pane: str = "") -> str:
    """Capture pane content from the active terminal multiplexer.

    Args:
        backend: "auto", "tmux", or "zellij"
        target_pane: For zellij: directional (left, right, up, down, next, previous).
            For tmux: pane identifier (e.g. "0:0.1"). Empty = current pane.
    """
    if backend == "auto":
        backend = detect_multiplexer()

    if backend == "tmux":
        return capture_tmux_pane(target_pane)
    elif backend == "zellij":
        return capture_zellij_pane(target_pane)
    else:
        raise ValueError(f"Unknown multiplexer backend: {backend}")
