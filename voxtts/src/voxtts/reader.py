"""Input text readers: file, clipboard, stdin, pane."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def read_file(path: str) -> str:
    """Read text from a file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return file_path.read_text(encoding="utf-8")


def read_clipboard() -> str:
    """Read text from system clipboard. Tries wl-paste (Wayland) then xclip (X11)."""
    # Try Wayland first
    try:
        result = subprocess.run(["wl-paste"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
    except FileNotFoundError:
        pass

    # Try X11
    try:
        result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
    except FileNotFoundError:
        pass

    raise RuntimeError(
        "No clipboard tool found. Install wl-paste (Wayland) or xclip (X11)."
    )


def read_stdin() -> str:
    """Read text from piped stdin."""
    if sys.stdin.isatty():
        raise RuntimeError("No input piped to stdin.")
    return sys.stdin.read()


def read_pane(backend: str = "auto", target_pane: str = "") -> str:
    """Read text from a tmux/zellij pane. Delegates to multiplexer module."""
    from voxtts.multiplexer import capture_pane
    return capture_pane(backend=backend, target_pane=target_pane)


def get_input_text(
    input_file: str | None = None,
    clipboard: bool = False,
    pane: bool = False,
    pane_target: str = "",
    backend: str = "auto",
) -> str:
    """Dispatcher: get input text based on CLI args.

    Priority: input_file > clipboard > pane > stdin
    """
    if input_file:
        return read_file(input_file)
    if clipboard:
        return read_clipboard()
    if pane:
        return read_pane(backend=backend, target_pane=pane_target)
    if not sys.stdin.isatty():
        return read_stdin()
    raise RuntimeError("No input text source specified.")
