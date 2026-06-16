"""Error hierarchy + exit-code mapping for lince-lab (blueprint §4).

Every :class:`LabError` carries an ``.exit_code`` so the CLI can propagate a
single, agreed-upon exit code through broker → client → process. The numeric
constants follow the BSD ``sysexits`` convention where one applies, plus a
project-specific ``POLICY_DENIED`` code.

Note on the *guest/recipe* exit code: a failing command inside a VM (e.g.
``make test`` returning 1) is **not** an error here — it is the signal the
bisect loop and oracle chaining rely on. Such codes flow through
:class:`~lince_lab.backend.ExecResult` and are propagated verbatim by the CLI,
never raised as a :class:`LabError`.
"""

from __future__ import annotations

# ── exit-code constants (blueprint §4) ──────────────────────────────────────
# Project-specific: a policy gate refused the request.
POLICY_DENIED = 13
# sysexits EX_USAGE: a verb outside the closed whitelist was requested.
UNKNOWN_VERB = 64
# sysexits EX_DATAERR: malformed recipe/config/protocol payload.
DATA_ERROR = 65
# sysexits EX_UNAVAILABLE: the broker socket could not be reached.
BROKER_UNREACHABLE = 69


class LabError(Exception):
    """Base class for every lince-lab error.

    Subclasses pin ``exit_code`` as a class attribute; instances may override it
    per-construction (rarely needed). The message is the human-facing reason.
    """

    exit_code: int = 1

    def __init__(self, message: str, *, exit_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if exit_code is not None:
            self.exit_code = exit_code


class PolicyDenied(LabError):
    """A policy gate refused the request (no host mounts, secret injection, ...)."""

    exit_code = POLICY_DENIED


class UnknownVerb(LabError):
    """The requested verb is not in the closed protocol whitelist."""

    exit_code = UNKNOWN_VERB


class DataError(LabError):
    """A recipe, config, or protocol payload was malformed or failed validation."""

    exit_code = DATA_ERROR


class BrokerUnreachable(LabError):
    """The broker unix socket could not be reached / the connection broke."""

    exit_code = BROKER_UNREACHABLE


class BackendError(LabError):
    """A backend lifecycle operation failed (create/start/stop/delete/snapshot).

    Defaults to the generic exit code 1; backend glue may raise with a more
    specific code where one applies.
    """

    exit_code = 1
