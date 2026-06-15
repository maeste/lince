"""Wire protocol for the lince-lab broker (blueprint §3).

Transport is newline-delimited JSON over an ``AF_UNIX`` stream: one request
object → one response object. This module owns the envelope shape, the closed
verb whitelist, and the ok/error response constructors. It is pure (no sockets)
so it is exhaustively unit-testable.

Request envelope::

    {"v": 1, "id": "<uuid>", "verb": "vm.exec",
     "args": {"name": "lab", "argv": ["sh", "-c", "make test"]}}

Success response::

    {"v": 1, "id": "<uuid>", "ok": true, "result": {...}}

Error response::

    {"v": 1, "id": "<uuid>", "ok": false,
     "error": {"code": "POLICY_DENIED", "message": "...", "exit": 13}}

The ``error.exit`` field is the CLI exit code to propagate (see
:mod:`lince_lab.errors`).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from lince_lab.errors import DataError, UnknownVerb

# Protocol version carried by every envelope. Bumped only on a breaking change.
PROTOCOL_VERSION = 1

# ── closed verb whitelist (blueprint §3) ────────────────────────────────────
# Anything not in this set is rejected with UNKNOWN_VERB (exit 64). There is
# deliberately no raw-shell / passthrough verb: the agent can only run argv that
# the broker policy-checks.
VERBS: frozenset[str] = frozenset(
    {
        # lifecycle
        "vm.create",
        "vm.start",
        "vm.stop",
        "vm.delete",
        "vm.status",
        "vm.list",
        # exec / files
        "vm.exec",
        "vm.copy_in",
        "vm.copy_out",
        # snapshots
        "snap.create",
        "snap.apply",
        "snap.delete",
        "snap.list",
        # recipe / bisect orchestration
        "recipe.validate",
        "recipe.run",
        "bisect.run",
        # capture channel verbs (upgrade the connection to a line stream)
        "capture.open",
        "capture.send",
        "capture.snapshot",
        # liveness
        "ping",
    }
)


def is_known_verb(verb: str) -> bool:
    """Return ``True`` iff ``verb`` is in the closed whitelist."""
    return verb in VERBS


def new_id() -> str:
    """Return a fresh request id."""
    return str(uuid.uuid4())


# ── envelope construction ───────────────────────────────────────────────────


def make_request(verb: str, args: dict[str, Any] | None = None, *, request_id: str | None = None) -> dict[str, Any]:
    """Build a request envelope.

    Raises :class:`~lince_lab.errors.UnknownVerb` if ``verb`` is not whitelisted,
    so a client can never put an out-of-band verb on the wire.
    """
    if not is_known_verb(verb):
        raise UnknownVerb(f"unknown verb: {verb!r}")
    return {
        "v": PROTOCOL_VERSION,
        "id": request_id or new_id(),
        "verb": verb,
        "args": dict(args or {}),
    }


def make_ok(request_id: str, result: Any) -> dict[str, Any]:
    """Build a success response carrying ``result``."""
    return {"v": PROTOCOL_VERSION, "id": request_id, "ok": True, "result": result}


def make_error(request_id: str, code: str, message: str, exit_code: int) -> dict[str, Any]:
    """Build an error response. ``exit_code`` lands in ``error.exit``."""
    return {
        "v": PROTOCOL_VERSION,
        "id": request_id,
        "ok": False,
        "error": {"code": code, "message": message, "exit": exit_code},
    }


def make_event(event: str, data: Any) -> dict[str, Any]:
    """Build an asynchronous capture-channel event frame (blueprint §3)."""
    return {"v": PROTOCOL_VERSION, "event": event, "data": data}


# ── newline-delimited JSON codec ────────────────────────────────────────────


def encode(obj: dict[str, Any]) -> bytes:
    """Encode one envelope as a single newline-terminated JSON line (UTF-8).

    ``sort_keys`` keeps output deterministic, which makes wire-level assertions
    and golden tests stable.
    """
    return (json.dumps(obj, sort_keys=True) + "\n").encode("utf-8")


def decode(line: bytes | str) -> dict[str, Any]:
    """Decode one JSON line into an envelope dict.

    Raises :class:`~lince_lab.errors.DataError` if the line is not valid JSON or
    does not decode to an object.
    """
    if isinstance(line, bytes):
        text = line.decode("utf-8")
    else:
        text = line
    text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataError(f"malformed protocol line: {exc}") from exc
    if not isinstance(obj, dict):
        raise DataError(f"protocol line did not decode to an object: {type(obj).__name__}")
    return obj


def validate_request(obj: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Validate a decoded request envelope.

    Returns ``(request_id, verb, args)``. Raises :class:`~lince_lab.errors.DataError`
    for a structurally invalid envelope and :class:`~lince_lab.errors.UnknownVerb`
    for a verb outside the whitelist (so the broker can map it to exit 64).
    """
    if obj.get("v") != PROTOCOL_VERSION:
        raise DataError(f"unsupported protocol version: {obj.get('v')!r}")
    request_id = obj.get("id")
    if not isinstance(request_id, str) or not request_id:
        raise DataError("request missing string 'id'")
    verb = obj.get("verb")
    if not isinstance(verb, str):
        raise DataError("request missing string 'verb'")
    if not is_known_verb(verb):
        raise UnknownVerb(f"unknown verb: {verb!r}")
    args = obj.get("args", {})
    if not isinstance(args, dict):
        raise DataError("request 'args' must be an object")
    return request_id, verb, args
