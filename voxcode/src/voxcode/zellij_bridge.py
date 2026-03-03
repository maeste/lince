"""Zellij integration for sending text to Claude Code pane."""

import os
import shutil
import subprocess

DIRECTIONAL_TARGETS = {"left", "right", "up", "down"}
CYCLE_TARGETS = {"next", "previous"}
VALID_TARGETS = DIRECTIONAL_TARGETS | CYCLE_TARGETS

OPPOSITE_DIRECTION = {
    "left": "right",
    "right": "left",
    "up": "down",
    "down": "up",
    "next": "previous",
    "previous": "next",
}


class ZellijBridge:
    """Sends text to a Zellij pane running Claude Code.

    Supports two navigation modes:
    - Cycle targets (next/previous): uses focus-next-pane / focus-previous-pane
    - Directional targets (left/right/up/down): uses move-focus for deterministic
      targeting in layouts with 3+ panes
    """

    def __init__(
        self,
        target_pane: str | None = None,
        auto_detect: bool = True,
        send_enter: bool = False,
    ):
        self.target_pane = target_pane
        self.auto_detect = auto_detect
        self.send_enter = send_enter

    def validate(self) -> None:
        """Check that Zellij is available, we are inside a session, and target is valid."""
        if not shutil.which("zellij"):
            raise RuntimeError("zellij is not installed. Install it from https://zellij.dev")
        if not os.environ.get("ZELLIJ") and not os.environ.get("ZELLIJ_SESSION_NAME"):
            raise RuntimeError(
                "Not inside a Zellij session. Start Zellij first, then run VoxCode inside it."
            )
        if self.target_pane and self.target_pane not in VALID_TARGETS:
            valid = ", ".join(sorted(VALID_TARGETS))
            raise RuntimeError(
                f"Invalid target_pane '{self.target_pane}'. Valid values: {valid}"
            )

    def get_target_pane(self) -> str:
        """Get the target pane direction.

        Returns a direction string. For cycle targets (next/previous), uses
        pane cycling. For directional targets (left/right/up/down), uses
        deterministic spatial navigation.
        """
        if self.target_pane:
            return self.target_pane
        return "next"

    def _focus_pane(self, direction: str) -> None:
        """Focus a pane using the appropriate zellij command for the direction."""
        if direction in DIRECTIONAL_TARGETS:
            subprocess.run(
                ["zellij", "action", "move-focus", direction],
                check=True,
            )
        else:
            subprocess.run(
                ["zellij", "action", f"focus-{direction}-pane"],
                check=True,
            )

    def send_text(self, text: str) -> None:
        """Send text to the Claude Code pane via Zellij focus-switch.

        When send_enter=False: focus Claude pane, write text, stay on Claude pane.
        When send_enter=True: focus Claude pane, write text, send Enter, focus back.
        """
        direction = self.get_target_pane()
        opposite = OPPOSITE_DIRECTION[direction]

        self._focus_pane(direction)

        subprocess.run(
            ["zellij", "action", "write-chars", text],
            check=True,
        )

        if self.send_enter:
            subprocess.run(
                ["zellij", "action", "write", "13"],
                check=True,
            )
            self._focus_pane(opposite)
