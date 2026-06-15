"""Broker server — the host-side mediator between agent and VM (blueprint §3).

:class:`BrokerServer` listens on an ``AF_UNIX`` ``SOCK_STREAM`` socket (mode
``0600``, owner-only), accepts one connection at a time, and for each request:

1. decodes + validates the envelope (a malformed line → ``DATA_ERROR`` / 65; an
   unknown verb → ``UNKNOWN_VERB`` / 64 — both surfaced as ``error.exit``);
2. runs :func:`lince_lab.policy.check` (the client-untrusted gate; a violation →
   ``POLICY_DENIED`` / 13);
3. dispatches the policy-cleaned args to the injected :class:`Backend`
   (``vm.*`` / ``snap.*``), to :mod:`lince_lab.recipe` (``recipe.validate`` /
   ``recipe.run``), to :mod:`lince_lab.bisect` (``bisect.run``), or upgrades the
   connection to a line stream for ``capture.*``;
4. writes one response envelope, carrying ``error.exit`` on failure.

The server is single-threaded but guards each VM with a per-VM lock so a future
threaded accept loop serializes operations on the same instance. It is
constructed with an injected :class:`Backend` — ``FakeBackend`` in tests,
``LimaBackend`` in production — so the whole dispatch path is exercisable over a
real unix socket with no VM.
"""

from __future__ import annotations

import os
import socket
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from lince_lab import protocol
from lince_lab.backend import Backend, ExecResult, VmState
from lince_lab.capture import Capture
from lince_lab.errors import DataError, LabError
from lince_lab.policy import check as policy_check
from lince_lab.recipe import load_recipe, run_recipe, validate


class BrokerServer:
    """A single-threaded unix-socket broker over an injected :class:`Backend`."""

    def __init__(
        self,
        socket_path: str | Path,
        backend: Backend,
        config: dict[str, Any] | None = None,
        *,
        home: Path | None = None,
    ) -> None:
        self.socket_path = str(socket_path)
        self.backend = backend
        self.config = dict(config or {})
        self.home = home
        self._sock: socket.socket | None = None
        self._locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._stop = threading.Event()
        self._dispatch: dict[str, Callable[[dict[str, Any]], Any]] = self._build_dispatch()

    # ── server lifecycle ─────────────────────────────────────────────────────
    def bind(self) -> None:
        """Create the listening socket at ``socket_path`` with mode ``0600``."""
        sock_path = Path(self.socket_path)
        sock_path.parent.mkdir(parents=True, exist_ok=True)
        if sock_path.exists():
            sock_path.unlink()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.socket_path)
        os.chmod(self.socket_path, 0o600)
        sock.listen(8)
        self._sock = sock

    def serve_forever(self) -> None:
        """Accept and handle connections until :meth:`stop` is called."""
        if self._sock is None:
            self.bind()
        assert self._sock is not None
        self._sock.settimeout(0.25)
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                try:
                    self.handle_connection(conn)
                except OSError:
                    pass

    def stop(self) -> None:
        """Signal the accept loop to exit and close the listening socket."""
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
        # Best-effort unlink so a restart can rebind cleanly.
        try:
            Path(self.socket_path).unlink()
        except FileNotFoundError:
            pass

    # ── per-connection handling ──────────────────────────────────────────────
    def handle_connection(self, conn: socket.socket) -> None:
        """Serve newline-JSON requests on ``conn`` until the peer closes it."""
        rbuf = bytearray()
        while True:
            line = _read_line(conn, rbuf)
            if line is None:
                return
            response, capture_setup = self._handle_line(line)
            conn.sendall(protocol.encode(response))
            if capture_setup is not None:
                # capture.open succeeded: upgrade this connection to a line stream.
                self._run_capture_stream(conn, rbuf, capture_setup)
                return

    def _handle_line(self, line: bytes) -> tuple[dict[str, Any], "_CaptureSetup | None"]:
        """Decode + dispatch one request line; return ``(response, capture_setup)``.

        ``capture_setup`` is non-``None`` only for a successful ``capture.open``,
        signaling the caller to upgrade the connection to a capture line stream.
        """
        request_id = "unknown"
        try:
            envelope = protocol.decode(line)
            request_id, verb, args = protocol.validate_request(envelope)
            return self._dispatch_request(request_id, verb, args)
        except LabError as exc:
            code = type(exc).__name__
            return protocol.make_error(request_id, code, str(exc), exc.exit_code), None
        except Exception as exc:  # noqa: BLE001 - last-resort guard; never leak a stack
            return (
                protocol.make_error(request_id, "INTERNAL", f"broker internal error: {exc}", 1),
                None,
            )

    def _dispatch_request(
        self, request_id: str, verb: str, args: dict[str, Any]
    ) -> tuple[dict[str, Any], "_CaptureSetup | None"]:
        """Policy-check then route a validated request to its handler."""
        recipe_ctx = self._recipe_ctx_for(verb, args)
        safe_args = policy_check(verb, args, recipe_ctx, home=self.home)

        if verb == "capture.open":
            setup = self._open_capture(safe_args)
            return protocol.make_ok(request_id, {"opened": True}), setup

        handler = self._dispatch.get(verb)
        if handler is None:
            # capture.send / capture.snapshot off-stream, or an unrouted verb.
            raise DataError(f"verb {verb!r} is not valid outside a capture stream")

        vm_name = args.get("name")
        if isinstance(vm_name, str) and vm_name:
            with self._locks[vm_name]:
                result = handler(safe_args)
        else:
            result = handler(safe_args)
        return protocol.make_ok(request_id, result), None

    # ── recipe context (server-side trusted facts for policy) ────────────────
    def _recipe_ctx_for(self, verb: str, args: dict[str, Any]) -> dict[str, Any]:
        """Build the trusted recipe context a policy check for ``verb`` needs.

        For ``recipe.run`` / ``bisect.run`` it loads the recipe and exposes its
        workspace dir + network posture; for ``vm.copy_in`` it passes through a
        caller-provided ``workspace_dir`` (the broker sets this during a recipe
        run). Recipe-load failures surface as ``DATA_ERROR`` to the client.
        """
        if verb in ("recipe.run", "bisect.run", "recipe.validate"):
            recipe_path = args.get("recipe")
            if isinstance(recipe_path, str) and recipe_path:
                recipe = load_recipe(recipe_path)
                workspace = recipe.workspace.get("host_dir")
                workspace_dir = str((recipe.source_dir / str(workspace)).resolve()) if workspace else None
                return {"workspace_dir": workspace_dir, "network": recipe.network}
        if verb == "vm.copy_in":
            return {"workspace_dir": args.get("workspace_dir")}
        return {}

    # ── verb routing table ───────────────────────────────────────────────────
    def _build_dispatch(self) -> dict[str, Callable[[dict[str, Any]], Any]]:
        return {
            "ping": self._h_ping,
            "vm.create": self._h_create,
            "vm.start": self._h_start,
            "vm.stop": self._h_stop,
            "vm.delete": self._h_delete,
            "vm.status": self._h_status,
            "vm.list": self._h_list,
            "vm.exec": self._h_exec,
            "vm.copy_in": self._h_copy_in,
            "vm.copy_out": self._h_copy_out,
            "snap.create": self._h_snap_create,
            "snap.apply": self._h_snap_apply,
            "snap.delete": self._h_snap_delete,
            "snap.list": self._h_snap_list,
            "recipe.validate": self._h_recipe_validate,
            "recipe.run": self._h_recipe_run,
            "bisect.run": self._h_bisect_run,
        }

    # ── liveness ─────────────────────────────────────────────────────────────
    def _h_ping(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"pong": True, "v": protocol.PROTOCOL_VERSION}

    # ── lifecycle ────────────────────────────────────────────────────────────
    def _h_create(self, args: dict[str, Any]) -> dict[str, Any]:
        # Template is forced server-side: policy stripped any client one, so the
        # broker supplies the (possibly empty) template the backend should use.
        template = args.get("template_yaml") or self.config.get("template_yaml", "")
        self.backend.create(args["name"], str(template))
        return {"created": args["name"]}

    def _h_start(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.start(args["name"])
        return {"started": args["name"]}

    def _h_stop(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.stop(args["name"], force=bool(args.get("force", False)))
        return {"stopped": args["name"]}

    def _h_delete(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.delete(args["name"], force=bool(args.get("force", False)))
        return {"deleted": args["name"]}

    def _h_status(self, args: dict[str, Any]) -> dict[str, Any]:
        return _vmstate_to_dict(self.backend.status(args["name"]))

    def _h_list(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        return [_vmstate_to_dict(s) for s in self.backend.list()]

    # ── exec / files ─────────────────────────────────────────────────────────
    def _h_exec(self, args: dict[str, Any]) -> dict[str, Any]:
        argv = [str(a) for a in (args.get("argv") or [])]
        env = args.get("env") if isinstance(args.get("env"), dict) else None
        result: ExecResult = self.backend.exec(
            args["name"],
            argv,
            workdir=args.get("workdir"),
            env=env,
            timeout=args.get("timeout"),
        )
        return {"exit_code": result.exit_code, "stdout": result.stdout, "stderr": result.stderr}

    def _h_copy_in(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.copy_in(
            args["name"],
            str(args["host_path"]),
            str(args["guest_path"]),
            recursive=bool(args.get("recursive", False)),
        )
        return {"copied_in": args["guest_path"]}

    def _h_copy_out(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.copy_out(
            args["name"],
            str(args["guest_path"]),
            str(args["host_path"]),
            recursive=bool(args.get("recursive", False)),
        )
        return {"copied_out": args["host_path"]}

    # ── snapshots ────────────────────────────────────────────────────────────
    def _h_snap_create(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.snapshot_create(args["name"], str(args["tag"]))
        return {"snapshot": args["tag"]}

    def _h_snap_apply(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.snapshot_apply(args["name"], str(args["tag"]))
        return {"applied": args["tag"]}

    def _h_snap_delete(self, args: dict[str, Any]) -> dict[str, Any]:
        self.backend.snapshot_delete(args["name"], str(args["tag"]))
        return {"deleted": args["tag"]}

    def _h_snap_list(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"snapshots": self.backend.snapshot_list(args["name"])}

    # ── recipe / bisect ──────────────────────────────────────────────────────
    def _h_recipe_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        recipe = load_recipe(str(args["recipe"]))
        validate(recipe, self.config or None)
        return {"valid": True, "recipe": recipe.name}

    def _h_recipe_run(self, args: dict[str, Any]) -> dict[str, Any]:
        recipe = load_recipe(str(args["recipe"]))
        exit_code = run_recipe(self.backend, recipe, self.config, keep=bool(args.get("keep", False)))
        return {"exit_code": exit_code, "recipe": recipe.name}

    def _h_bisect_run(self, args: dict[str, Any]) -> dict[str, Any]:
        from lince_lab.bisect import run_bisect

        recipe = load_recipe(str(args["recipe"]))
        document = run_bisect(
            self.backend,
            recipe,
            self.config,
            good=str(args["good"]),
            bad=str(args["bad"]),
            repo_dir=str(args["repo_dir"]),
            out_path=str(args.get("out", "bisect.json")),
            keep=bool(args.get("keep", False)),
        )
        return document

    # ── capture stream ───────────────────────────────────────────────────────
    def _open_capture(self, args: dict[str, Any]) -> "_CaptureSetup":
        program = [str(a) for a in (args.get("program") or [])]
        cols, rows = _parse_size(str(args.get("size", "80x24")))
        channel = self.backend.open_capture(args["name"], program, cols, rows)
        return _CaptureSetup(Capture(channel, cols, rows))

    def _run_capture_stream(self, conn: socket.socket, rbuf: bytearray, setup: "_CaptureSetup") -> None:
        """Serve ``capture.send`` / ``capture.snapshot`` over the upgraded stream.

        Each subsequent request on this connection drives the open
        :class:`Capture`; the response (or a snapshot/wait grid) is written back
        as a normal envelope. The stream ends when the peer closes the connection
        or sends ``capture.close``.
        """
        capture = setup.capture
        try:
            while True:
                line = _read_line(conn, rbuf)
                if line is None:
                    return
                request_id = "unknown"
                try:
                    envelope = protocol.decode(line)
                    request_id, verb, args = protocol.validate_request(envelope)
                    result = self._handle_capture_verb(capture, verb, args)
                    conn.sendall(protocol.encode(protocol.make_ok(request_id, result)))
                except LabError as exc:
                    conn.sendall(
                        protocol.encode(protocol.make_error(request_id, type(exc).__name__, str(exc), exc.exit_code))
                    )
                except Exception as exc:  # noqa: BLE001
                    conn.sendall(
                        protocol.encode(protocol.make_error(request_id, "INTERNAL", f"capture error: {exc}", 1))
                    )
        finally:
            capture.close()

    @staticmethod
    def _handle_capture_verb(capture: Capture, verb: str, args: dict[str, Any]) -> Any:
        """Route one in-stream capture request to the :class:`Capture` instance."""
        if verb == "capture.send":
            keys = args.get("keys")
            if keys is not None:
                capture.send_keys([str(k) for k in keys])
            elif "payload" in args:
                capture.input(str(args["payload"]))
            elif "wait_for" in args:
                grid = capture.wait_for_substring(str(args["wait_for"]), timeout_s=float(args.get("timeout_s", 60)))
                return _grid_to_dict(grid)
            elif "stable_ms" in args:
                grid = capture.wait_for_stable(int(args["stable_ms"]), timeout_s=float(args.get("timeout_s", 60)))
                return _grid_to_dict(grid)
            return {"sent": True}
        if verb == "capture.snapshot":
            grid = capture.snapshot(timeout_s=float(args.get("timeout_s", 5)))
            return _grid_to_dict(grid)
        raise DataError(f"verb {verb!r} is not a capture-stream verb")


class _CaptureSetup:
    """Carries the open :class:`Capture` from ``capture.open`` to the stream loop."""

    def __init__(self, capture: Capture) -> None:
        self.capture = capture


# ── module-level helpers ─────────────────────────────────────────────────────


def _read_line(conn: socket.socket, rbuf: bytearray) -> bytes | None:
    """Read one newline-terminated frame from ``conn``, buffering the remainder.

    Returns the line without its trailing newline, a final partial line at clean
    EOF, or ``None`` when the peer closes with nothing buffered.
    """
    while True:
        newline = rbuf.find(b"\n")
        if newline != -1:
            line = bytes(rbuf[:newline])
            del rbuf[: newline + 1]
            return line
        chunk = conn.recv(65536)
        if not chunk:
            if rbuf:
                line = bytes(rbuf)
                rbuf.clear()
                return line
            return None
        rbuf.extend(chunk)


def _vmstate_to_dict(state: VmState) -> dict[str, Any]:
    """Serialize a :class:`VmState` for the wire."""
    return {"name": state.name, "status": state.status.value, "snapshots": list(state.snapshots)}


def _grid_to_dict(grid: Any) -> dict[str, Any]:
    """Serialize a :class:`~lince_lab.capture.Grid` for the wire."""
    return {"cols": grid.cols, "rows": grid.rows, "text": grid.text}


def _parse_size(size: str) -> tuple[int, int]:
    """Parse ``"<cols>x<rows>"`` into ``(cols, rows)``; raise ``DataError`` if malformed."""
    try:
        cols_s, rows_s = size.lower().split("x", 1)
        return int(cols_s), int(rows_s)
    except (ValueError, AttributeError) as exc:
        raise DataError(f"invalid capture size {size!r}; expected '<cols>x<rows>'") from exc
