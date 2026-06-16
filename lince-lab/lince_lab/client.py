"""Broker client — the CLI-side socket transport (blueprint §3, §4).

:class:`BrokerClient` connects to the broker's ``AF_UNIX`` ``SOCK_STREAM`` socket,
writes one newline-delimited JSON request, reads one response line, and returns
the decoded ``result`` (or raises a :class:`~lince_lab.errors.LabError` carrying
the broker's ``error.exit`` so the CLI propagates the agreed exit code).

A missing socket / connection refused maps to
:class:`~lince_lab.errors.BrokerUnreachable` (exit 69, ``EX_UNAVAILABLE``) — the
"the broker isn't running" signal the CLI and oracles agree on.

The class is also a context manager so a caller can hold one connection open for
a capture session (the same connection upgrades to a bidirectional line stream
after ``capture.open``; :meth:`send`/:meth:`recv` expose that raw frame access).
"""

from __future__ import annotations

import socket
from pathlib import Path
from types import TracebackType
from typing import Any

from lince_lab import protocol
from lince_lab.errors import BrokerUnreachable, DataError, LabError


class BrokerClient:
    """A connection to the broker over its unix socket.

    Construct with the socket path, then call :meth:`call` for a single
    request/response round-trip, or :meth:`connect` + :meth:`send` / :meth:`recv`
    for a held-open capture stream. Either way, :meth:`close` (or the context
    manager) releases the socket.
    """

    def __init__(self, socket_path: str | Path, *, timeout: float | None = None) -> None:
        self.socket_path = str(socket_path)
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._rbuf = bytearray()

    # ── context manager ──────────────────────────────────────────────────────
    def __enter__(self) -> BrokerClient:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # ── connection lifecycle ─────────────────────────────────────────────────
    def connect(self) -> None:
        """Open the unix-socket connection to the broker.

        Raises :class:`~lince_lab.errors.BrokerUnreachable` (exit 69) if the
        socket file is missing or the broker is not accepting connections.
        """
        if self._sock is not None:
            return
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout is not None:
            sock.settimeout(self.timeout)
        try:
            sock.connect(self.socket_path)
        except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
            sock.close()
            raise BrokerUnreachable(
                f"cannot reach broker socket {self.socket_path!r}: {exc}; is `lince-lab lab broker start` running?"
            ) from exc
        self._sock = sock
        self._rbuf = bytearray()

    def close(self) -> None:
        """Close the connection (idempotent)."""
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
        self._rbuf = bytearray()

    # ── raw frame I/O (used by the capture stream) ───────────────────────────
    def send(self, obj: dict[str, Any]) -> None:
        """Write one envelope as a newline-JSON frame."""
        sock = self._require_sock()
        try:
            sock.sendall(protocol.encode(obj))
        except (BrokenPipeError, ConnectionResetError, OSError) as exc:
            raise BrokerUnreachable(f"broker connection broke while sending: {exc}") from exc

    def recv(self) -> dict[str, Any] | None:
        """Read and decode one newline-JSON frame, or ``None`` at clean EOF."""
        line = self._read_line()
        if line is None:
            return None
        return protocol.decode(line)

    # ── single round-trip ────────────────────────────────────────────────────
    def call(self, verb: str, args: dict[str, Any] | None = None) -> Any:
        """Send one request, read its response, and return ``result``.

        On an error response, raises a :class:`~lince_lab.errors.LabError` whose
        ``exit_code`` is the broker's ``error.exit`` — so the CLI exits with the
        single agreed code. Opens the connection on demand and (for a one-shot
        ``call``) closes it afterwards.
        """
        owned = self._sock is None
        if owned:
            self.connect()
        try:
            request = protocol.make_request(verb, args)
            self.send(request)
            response = self.recv()
            if response is None:
                raise BrokerUnreachable("broker closed the connection without responding")
            return self._unwrap(response, request["id"])
        finally:
            if owned:
                self.close()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _require_sock(self) -> socket.socket:
        if self._sock is None:
            raise BrokerUnreachable("client is not connected")
        return self._sock

    def _read_line(self) -> bytes | None:
        """Read one newline-terminated frame from the socket, buffering the rest.

        Delegates the frame-scanning to :func:`lince_lab.protocol.read_line`,
        wrapping the socket ``recv`` so a broken read raises
        :class:`~lince_lab.errors.BrokerUnreachable`.
        """
        sock = self._require_sock()

        def recv(size: int) -> bytes:
            try:
                return sock.recv(size)
            except (ConnectionResetError, OSError) as exc:
                raise BrokerUnreachable(f"broker connection broke while reading: {exc}") from exc

        return protocol.read_line(recv, self._rbuf)

    @staticmethod
    def _unwrap(response: dict[str, Any], request_id: str) -> Any:
        """Return ``result`` from a success response or raise on an error one."""
        if response.get("id") != request_id:
            raise DataError(f"broker response id {response.get('id')!r} does not match request {request_id!r}")
        if response.get("ok"):
            return response.get("result")
        error = response.get("error") or {}
        message = str(error.get("message", "broker error"))
        exit_code = error.get("exit")
        if not isinstance(exit_code, int):
            raise DataError(f"broker error response missing integer exit: {error!r}")
        raise LabError(message, exit_code=exit_code)
