"""Optional pixel capture: render a captured text grid to a PNG (blueprint §7, ADR-10).

ADR-10 keeps the **text grid** (``Grid.text``) as v1's canonical assertion
surface; a pixel/PNG renderer is an *independent output layer* over that same
text. This module is that layer, kept deliberately optional:

* :data:`PIL_AVAILABLE` reports whether Pillow is importable.
* :func:`grid_text_to_png` renders the grid text to PNG **bytes** using Pillow's
  default bitmap font (monospaced cell layout, one terminal row per line). It
  raises :class:`~lince_lab.errors.DataError` if Pillow is not installed — the
  caller (the ``watch grab --png`` path) checks :data:`PIL_AVAILABLE` first and
  falls back to a ``.txt`` artifact when Pillow is absent, so the PNG path is
  never a hard dependency.

No Pillow ⇒ no fake PNG: the only honest fallback is the text artifact (see the
CLI ``watch grab --png`` handler), never a hand-rolled invalid image.
"""

from __future__ import annotations

from lince_lab.errors import DataError

try:  # Pillow is an OPTIONAL dependency; the text-grid path never needs it.
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only on hosts without Pillow
    PIL_AVAILABLE = False


# Cell geometry for the default bitmap font (a safe, render-stable monospace box).
_CELL_W = 8
_CELL_H = 16
_PAD = 4
_BG = (12, 12, 12)
_FG = (220, 220, 220)


def grid_text_to_png(text: str, cols: int, rows: int) -> bytes:
    """Render ``text`` (one terminal row per line) to PNG bytes.

    The image is sized to the grid: ``cols`` × ``rows`` cells plus a small pad.
    Each line is drawn left-aligned on its row with Pillow's default font. Raises
    :class:`~lince_lab.errors.DataError` if Pillow is unavailable — callers must
    gate on :data:`PIL_AVAILABLE` and fall back to a text artifact instead.
    """
    if not PIL_AVAILABLE:
        raise DataError("pixel PNG capture requires the optional Pillow dependency (pip install Pillow)")

    lines = text.split("\n")
    width = max(cols, 1) * _CELL_W + 2 * _PAD
    height = max(rows, len(lines), 1) * _CELL_H + 2 * _PAD

    image = Image.new("RGB", (width, height), _BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for row_index, line in enumerate(lines):
        y = _PAD + row_index * _CELL_H
        draw.text((_PAD, y), line, fill=_FG, font=font)

    import io

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
