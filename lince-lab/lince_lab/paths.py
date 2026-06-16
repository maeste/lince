"""Shared path / name helpers with a single home each (DRY, security-relevant).

These small primitives were previously duplicated across :mod:`lince_lab.policy`,
:mod:`lince_lab.recipe`, and :mod:`lince_lab.bisect`. Keeping ONE implementation
matters most for :func:`resolves_under`: it is the path-bounding guard the broker
copy_in/copy_out policy and the recipe workspace validation both rely on, so the
two must never drift. The VM-name slugger and the ``<cols>x<rows>`` size parser
are co-located here for the same single-source reason.
"""

from __future__ import annotations

from pathlib import Path

from lince_lab.errors import DataError

# The policy VM-name namespace every lab VM carries. Imported by callers that
# build a VM name so the prefix is defined in exactly one place.
VM_NAME_PREFIX = "lince-lab-"


def resolves_under(base: Path, candidate: str) -> bool:
    """Return ``True`` iff ``candidate`` (relative to ``base``) stays under ``base``.

    Pure path math — never touches the filesystem. An absolute ``candidate``
    outside ``base`` or a relative one that climbs out via ``..`` is rejected.
    This is the single guard the broker copy-in/out policy and the recipe-level
    workspace validation share, so the same bound is enforced on the wire and in
    the recipe. ``candidate`` is expanded (``~``) before the comparison.
    """
    base_resolved = base.resolve()
    target = Path(candidate).expanduser()
    combined = target if target.is_absolute() else base_resolved / target
    resolved = combined.resolve()
    if resolved == base_resolved:
        return True
    return base_resolved in resolved.parents


def slug_vm_name(name: str, prefix: str = VM_NAME_PREFIX) -> str:
    """Build a policy-prefixed VM name from a recipe ``name``.

    Non-``[A-Za-z0-9-]`` characters are replaced with ``-`` so the result is a
    safe instance name; an empty slug falls back to ``recipe``. ``prefix`` lets
    the bisect loop interpose its own ``lince-lab-bisect-`` namespace while reusing
    the same slugging rule.
    """
    safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in name) or "recipe"
    return f"{prefix}{safe}"


def parse_size(size: str) -> tuple[int, int]:
    """Parse a ``"<cols>x<rows>"`` grid size into an ``(cols, rows)`` tuple.

    Raises :class:`~lince_lab.errors.DataError` (exit 65) on a malformed size.
    """
    try:
        cols_s, rows_s = size.lower().split("x", 1)
        return int(cols_s), int(rows_s)
    except (ValueError, AttributeError) as exc:
        raise DataError(f"invalid capture size {size!r}; expected '<cols>x<rows>'") from exc
