"""Interactive startup wizard for mode and audio device selection."""

import os
import sys
import termios
import tty

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def _read_key(fd: int) -> str:
    """Read a keypress from raw terminal, handling arrow escape sequences."""
    ch = os.read(fd, 1).decode("utf-8", errors="ignore")
    if ch == "\x1b":
        seq = os.read(fd, 1).decode("utf-8", errors="ignore")
        if seq == "[":
            code = os.read(fd, 1).decode("utf-8", errors="ignore")
            if code == "A":
                return "up"
            if code == "B":
                return "down"
            # Drain any remaining bytes from extended sequences (e.g. \x1b[1;5A)
            while code and code[-1] not in "ABCDEFGHPQRS~":
                extra = os.read(fd, 1).decode("utf-8", errors="ignore")
                if not extra:
                    break
                code = extra
        return "escape"
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "q":
        return "quit"
    return ch


def _render_menu(console: Console, title: str, items: list[str], selected: int) -> None:
    """Render a selection menu inside a Rich panel."""
    lines = Text()
    lines.append(f"  {title}\n\n", style="bold")
    for i, item in enumerate(items):
        if i == selected:
            lines.append(f"  > {item}\n", style="bold green")
        else:
            lines.append(f"    {item}\n", style="dim")
    lines.append("\n  ↑↓ navigate  Enter confirm  q quit", style="dim")
    console.clear()
    console.print(Panel(lines, title="[bold blue]VoxCode Setup[/]", border_style="blue", expand=False))


def _select_menu(console: Console, fd: int, title: str, items: list[str], default: int = 0) -> int | None:
    """Show an interactive menu and return selected index, or None if user quits."""
    selected = default
    while True:
        _render_menu(console, title, items, selected)
        key = _read_key(fd)
        if key == "up":
            selected = (selected - 1) % len(items)
        elif key == "down":
            selected = (selected + 1) % len(items)
        elif key == "enter":
            return selected
        elif key == "quit":
            return None


def _get_input_devices() -> list[dict]:
    """Return list of input-capable audio devices with their indices."""
    import sounddevice as sd

    devices = sd.query_devices()
    default_input = sd.default.device[0]
    result = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            result.append({
                "index": i,
                "name": dev["name"],
                "channels": dev["max_input_channels"],
                "rate": int(dev["default_samplerate"]),
                "is_default": i == default_input,
            })
    return result


def run_wizard(ask_mode: bool = True, ask_device: bool = True) -> tuple[str | None, int | None]:
    """Run the startup wizard.

    Args:
        ask_mode: Whether to ask for input mode selection.
        ask_device: Whether to ask for audio device selection.

    Returns:
        Tuple of (selected_mode, selected_device_index).
        Values are None if not asked or user quit.
    """
    if not sys.stdin.isatty():
        return (None, None)

    console = Console()
    selected_mode: str | None = None
    selected_device: int | None = None

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    try:
        # Step 1: Mode selection
        if ask_mode:
            mode_items = [
                "PTT (push-to-talk)  [default]",
                "VAD (voice activity detection)",
            ]
            result = _select_menu(console, fd, "Select input mode:", mode_items, default=0)
            if result is None:
                console.clear()
                return (None, None)
            selected_mode = "ptt" if result == 0 else "vad"

        # Step 2: Device selection
        if ask_device:
            devices = _get_input_devices()
            if not devices:
                console.print("[red]No input audio devices found.[/]")
                return (selected_mode, None)

            default_idx = 0
            device_items = []
            for i, dev in enumerate(devices):
                label = f"{dev['index']}: {dev['name']}  ({dev['channels']}ch, {dev['rate']}Hz)"
                if dev["is_default"]:
                    label += "  [default]"
                    default_idx = i
                device_items.append(label)

            result = _select_menu(console, fd, "Select audio input device:", device_items, default=default_idx)
            if result is None:
                console.clear()
                return (selected_mode, None)
            selected_device = devices[result]["index"]
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    console.clear()
    return (selected_mode, selected_device)
