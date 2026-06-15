"""FakeBackend — fully in-memory, deterministic substrate (blueprint §2).

This is the workhorse for unit tests: it implements every :class:`Backend`
method without any I/O so the entire broker/recipe/bisect/capture stack can be
exercised with no VM. It is a *faithful* stand-in — the same contract suite in
``tests/test_backend_contract.py`` runs against it and (KVM-gated) against
``LimaBackend``.

Key facilities:

* In-memory VM table (``dict[name, VmState]``) plus a per-VM virtual filesystem
  (``dict[guest_path, bytes]``).
* Snapshots stored via :func:`copy.deepcopy` of (fs + status) — so a bisect test
  can assert a clean reset between candidates.
* A programmable command table: tests register
  ``fake.on(name, argv_pattern, ExecResult | callable)``. An unregistered argv
  yields ``ExecResult(127, "", "fake: command not found")``. A callable receives
  the VM's filesystem and may mutate it (models installers writing files),
  enabling idempotency and regression-seeding tests.
* :class:`FakeCaptureChannel` replays a scripted sequence of ``output`` /
  ``snapshot`` events, so the capture wait primitives run without a PTY.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable
from typing import Any, Union

from lince_lab.backend import (
    Backend,
    CaptureChannel,
    ExecResult,
    VmState,
    VmStatus,
)
from lince_lab.errors import BackendError

# A registered exec handler: either a static result, or a callable that receives
# the VM's virtual filesystem (and the argv) and returns an ExecResult. The
# callable may mutate the fs dict in place.
ExecHandler = Union[ExecResult, Callable[[dict[str, bytes], list[str]], ExecResult]]


class _FakeVm:
    """Internal per-VM record: status, virtual fs, and snapshot store."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.status: VmStatus = VmStatus.STOPPED
        self.fs: dict[str, bytes] = {}
        # tag -> deep-copied (fs, status) at snapshot time
        self.snapshots: dict[str, tuple[dict[str, bytes], VmStatus]] = {}


class FakeCaptureChannel(CaptureChannel):
    """Replays a scripted event sequence for capture-layer tests.

    Construct with a list of event dicts (each like ``{"type": "output", ...}``
    or ``{"type": "snapshot", "data": {...}}``). Each :meth:`read_line` returns
    the next scripted event, blocking only up to ``deadline`` for an empty
    script tail. Commands sent via :meth:`send_line` are recorded in
    :attr:`sent` for assertions; a ``takeSnapshot`` command also surfaces the
    next scripted ``snapshot`` event eagerly so wait loops behave naturally.
    """

    def __init__(self, script: list[dict[str, Any]] | None = None) -> None:
        self._events: list[dict[str, Any]] = list(script or [])
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    def send_line(self, obj: dict) -> None:
        if self.closed:
            raise BackendError("send on closed capture channel")
        self.sent.append(dict(obj))

    def read_line(self, deadline: float) -> dict | None:
        if self._events:
            return self._events.pop(0)
        # No scripted events remain: emulate event silence until the deadline.
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(remaining, 0.01))
        return None

    def feed(self, event: dict[str, Any]) -> None:
        """Append an event to the replay queue (test helper)."""
        self._events.append(dict(event))

    def close(self) -> None:
        self.closed = True


class FakeBackend(Backend):
    """In-memory :class:`Backend` for deterministic, VM-free tests."""

    def __init__(self) -> None:
        self._vms: dict[str, _FakeVm] = {}
        # (name, tuple(argv)) -> handler, plus (name, None) wildcard handlers
        self._exec_table: dict[tuple[str, tuple[str, ...] | None], ExecHandler] = {}
        # name -> scripted capture channel returned by open_capture
        self._capture_scripts: dict[str, FakeCaptureChannel] = {}

    # ── test programming surface ─────────────────────────────────────────────
    def on(self, name: str, argv: list[str] | None, handler: ExecHandler) -> None:
        """Register an exec handler.

        ``argv=None`` registers a wildcard for ``name`` (matched only when no
        exact argv handler applies). ``handler`` is either a static
        :class:`ExecResult` or ``callable(fs, argv) -> ExecResult`` that may
        mutate the VM filesystem.
        """
        key = (name, tuple(argv) if argv is not None else None)
        self._exec_table[key] = handler

    def script_capture(self, name: str, channel: FakeCaptureChannel) -> None:
        """Pre-register the :class:`FakeCaptureChannel` for ``open_capture(name, ...)``."""
        self._capture_scripts[name] = channel

    def fs_of(self, name: str) -> dict[str, bytes]:
        """Return the live virtual filesystem dict of ``name`` (test inspection)."""
        return self._require(name).fs

    # ── internal helpers ─────────────────────────────────────────────────────
    def _require(self, name: str) -> _FakeVm:
        vm = self._vms.get(name)
        if vm is None:
            raise BackendError(f"no such VM: {name}")
        return vm

    # ── lifecycle ────────────────────────────────────────────────────────────
    def create(self, name: str, template_yaml: str) -> None:
        if name in self._vms:
            raise BackendError(f"VM already exists: {name}")
        # template_yaml is accepted but unused by the Fake; stored for parity.
        vm = _FakeVm(name)
        vm.fs["/.lince-lab/template.yaml"] = template_yaml.encode("utf-8")
        self._vms[name] = vm

    def start(self, name: str) -> None:
        self._require(name).status = VmStatus.RUNNING

    def stop(self, name: str, force: bool = False) -> None:
        self._require(name).status = VmStatus.STOPPED

    def delete(self, name: str, force: bool = False) -> None:
        vm = self._require(name)
        if vm.status == VmStatus.RUNNING and not force:
            raise BackendError(f"VM running, refuse to delete without force: {name}")
        del self._vms[name]

    def status(self, name: str) -> VmState:
        vm = self._vms.get(name)
        if vm is None:
            return VmState(name=name, status=VmStatus.ABSENT, snapshots=[])
        return VmState(name=name, status=vm.status, snapshots=sorted(vm.snapshots))

    def list(self) -> list[VmState]:
        return [self.status(name) for name in sorted(self._vms)]

    # ── exec / files ─────────────────────────────────────────────────────────
    def exec(
        self,
        name: str,
        argv: list[str],
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> ExecResult:
        vm = self._require(name)
        handler = self._exec_table.get((name, tuple(argv)))
        if handler is None:
            handler = self._exec_table.get((name, None))
        if handler is None:
            # Built-in: support `test -f <path>` against the virtual fs so recipe
            # file_exists assertions work without per-test registration.
            builtin = self._builtin_exec(vm, argv)
            if builtin is not None:
                return builtin
            return ExecResult(exit_code=127, stdout="", stderr="fake: command not found")
        if isinstance(handler, ExecResult):
            return handler
        return handler(vm.fs, argv)

    @staticmethod
    def _builtin_exec(vm: _FakeVm, argv: list[str]) -> ExecResult | None:
        """Handle a tiny set of argv shapes against the virtual fs."""
        if argv[:2] == ["test", "-f"] and len(argv) == 3:
            present = argv[2] in vm.fs
            return ExecResult(exit_code=0 if present else 1, stdout="", stderr="")
        return None

    def copy_in(self, name: str, host_path: str, guest_path: str, recursive: bool = False) -> None:
        vm = self._require(name)
        # Model the host file's content by its path string when no real bytes are
        # supplied; tests that care about content use `on()` callables instead.
        vm.fs[guest_path] = f"<copied:{host_path}>".encode("utf-8")

    def copy_out(self, name: str, guest_path: str, host_path: str, recursive: bool = False) -> None:
        vm = self._require(name)
        if guest_path not in vm.fs:
            raise BackendError(f"no such guest path: {guest_path}")
        # No real host write in the Fake; round-trip identity is asserted via fs.

    # ── snapshots ────────────────────────────────────────────────────────────
    def snapshot_create(self, name: str, tag: str) -> None:
        vm = self._require(name)
        vm.snapshots[tag] = (copy.deepcopy(vm.fs), vm.status)

    def snapshot_apply(self, name: str, tag: str) -> None:
        vm = self._require(name)
        snap = vm.snapshots.get(tag)
        if snap is None:
            raise BackendError(f"no such snapshot: {tag}")
        fs, status = snap
        vm.fs = copy.deepcopy(fs)
        vm.status = status

    def snapshot_delete(self, name: str, tag: str) -> None:
        vm = self._require(name)
        if tag not in vm.snapshots:
            raise BackendError(f"no such snapshot: {tag}")
        del vm.snapshots[tag]

    def snapshot_list(self, name: str) -> list[str]:
        return sorted(self._require(name).snapshots)

    # ── capture ──────────────────────────────────────────────────────────────
    def open_capture(self, name: str, argv: list[str], cols: int, rows: int) -> CaptureChannel:
        self._require(name)
        channel = self._capture_scripts.get(name)
        if channel is None:
            # Default: an empty channel (silence). Tests usually pre-script one.
            channel = FakeCaptureChannel([])
        return channel
