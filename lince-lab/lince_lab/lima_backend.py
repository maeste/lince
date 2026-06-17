"""LimaBackend — the real, KVM-only substrate glue (blueprint §2).

This is the *only* KVM-dependent module: it shells out to ``limactl`` (QEMU on
Linux) for every :class:`~lince_lab.backend.Backend` operation. It is not run
against a real VM in the unit suite — the ``scripts/lince-lab/ci`` oracles do
that — but it is importable, ruff-clean, and its exact ``limactl`` argv
construction is unit-tested by mocking :mod:`subprocess`.

The mapping follows the verified limactl cheat-sheet (``claudedocs/lince-lab/
lima.md``) 1:1:

* ``create`` → ``limactl create --name N -`` (template YAML on stdin)
* ``start``  → ``limactl start N -y``
* ``stop``/``delete`` → ``limactl stop|delete N [-f]``
* ``status``/``list`` → ``limactl list [N] --json`` parsed into :class:`VmState`
* ``exec``   → ``limactl shell [--workdir W] N -- argv`` returning the guest
  exit code verbatim (it **never** raises on guest nonzero — that is the bisect
  signal)
* ``copy_in``/``copy_out`` → ``limactl copy [-r] SRC TGT`` with the ``N:path``
  form
* ``snapshot_*`` → ``limactl snapshot create|apply|delete|list N --tag TAG``
* ``open_capture`` → spawn ``limactl shell N -- ht --size CxR --subscribe
  init,output,snapshot -- argv`` wrapped in a :class:`LimaCaptureChannel` over
  stdio pipes.

Lifecycle verbs route through one :meth:`LimaBackend._run` helper that raises
:class:`~lince_lab.errors.BackendError` on a nonzero ``limactl`` exit. ``exec``
is deliberately kept separate so it can return the guest code without raising.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

from lince_lab.backend import (
    Backend,
    CaptureChannel,
    ExecResult,
    VmState,
    VmStatus,
)
from lince_lab.errors import BackendError

# The limactl executable name. Resolved on PATH; pinned/installed by the module
# install scripts. Kept as a module constant so tests can assert on argv[0].
LIMACTL = "limactl"

# Default headless-terminal binary name on the guest PATH (fallback when no
# host-side ht is available to copy in).
HT_BINARY = "ht"

# Where the host-side ht is copied to inside the guest. A disposable, world-safe
# /tmp path: it carries no host access — it is just our own capture driver.
GUEST_HT_PATH = "/tmp/lince-lab-ht"


def _host_ht_path() -> str:
    """Resolve the HOST-side ``ht`` binary path the broker ships and copies in.

    Honors ``$LINCE_LAB_HT`` if set; otherwise falls back to the lince-lab share
    dir's ``bin/ht`` (``$XDG_DATA_HOME`` then ``$HOME/.local/share``), matching the
    install/update scripts. The returned path is expanded (``~``) but not required
    to exist — :meth:`LimaBackend.open_capture` checks for it on disk and falls
    back to the bare guest ``ht`` when it is absent.
    """
    env = os.environ.get("LINCE_LAB_HT")
    if env:
        return str(Path(env).expanduser())
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return str((base / "lince" / "lince-lab" / "bin" / "ht").expanduser())


def _map_status(raw: str) -> VmStatus:
    """Map a ``limactl list --json`` status string to a :class:`VmStatus`.

    Lima reports ``Running`` / ``Stopped`` (and transient values like
    ``Starting``). Anything not clearly running is treated as stopped; an empty
    string (no record) maps to ``ABSENT`` by the caller, not here.
    """
    norm = raw.strip().lower()
    if norm == "running":
        return VmStatus.RUNNING
    return VmStatus.STOPPED


class LimaCaptureChannel(CaptureChannel):
    """A :class:`CaptureChannel` over a live ``limactl shell ... ht`` process.

    The wrapped process runs ``ht`` inside the guest with stdin/stdout pinned to
    pipes. Commands (``sendKeys`` / ``takeSnapshot`` / ...) are written as
    newline-delimited JSON to the process stdin; events (``output`` /
    ``snapshot`` / ...) are read as newline-delimited JSON from its stdout.

    :meth:`read_line` honours an absolute ``time.monotonic()`` ``deadline`` so
    the capture wait primitives stay sleep-free: it blocks on the readline
    thread's queue only until the deadline, returning ``None`` on silence.

    For diagnosability, ``ht``'s **stderr is drained on a background thread**
    (otherwise it is invisible and a full pipe could deadlock ht), and the tail
    of both streams plus the spawn argv and exit status are kept in ring buffers
    so :meth:`diagnostics` can explain a capture timeout (e.g. ``ht: command not
    found`` in a guest with no ht) instead of leaving a bare deadline.
    """

    def __init__(self, proc: subprocess.Popen[str], argv: list[str] | None = None) -> None:
        self._proc = proc
        self.closed = False
        # Spawn argv + bounded tails of each stream, for diagnostics() on timeout.
        self._argv = list(argv or [])
        self._stdout_tail: deque[str] = deque(maxlen=50)
        self._stderr_tail: deque[str] = deque(maxlen=50)
        # Drain stderr continuously so it is captured AND cannot fill the pipe and
        # wedge ht. A daemon thread ends on its own when ht closes stderr/exits.
        self._stderr_thread: threading.Thread | None = None
        if self._proc.stderr is not None:
            self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
            self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        stderr = self._proc.stderr
        if stderr is None:
            return
        try:
            for line in stderr:  # blocks until EOF; ht exit closes the pipe
                self._stderr_tail.append(line.rstrip("\n"))
        except (ValueError, OSError):
            # Pipe closed underneath us during teardown — nothing to drain.
            pass

    def send_line(self, obj: dict) -> None:
        if self.closed or self._proc.stdin is None:
            raise BackendError("send on closed capture channel")
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def read_line(self, deadline: float) -> dict | None:
        if self._proc.stdout is None:
            return None
        # Block on the pipe until a line arrives or the deadline elapses. We use
        # a short bounded poll (no fixed sleep semantics — the loop advances the
        # instant a line is available and returns the moment the deadline hits).
        while True:
            line = self._proc.stdout.readline()
            if line:
                stripped = line.strip()
                if not stripped:
                    continue
                self._stdout_tail.append(stripped[:500])
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    # Skip non-JSON noise (e.g. ssh banners) rather than fail.
                    continue
            # EOF or empty read: respect the deadline.
            if time.monotonic() >= deadline:
                return None
            if self._proc.poll() is not None:
                return None

    def diagnostics(self) -> str:
        """Explain what ``ht`` did — argv, exit status, and stderr/stdout tails."""
        rc = self._proc.poll()
        status = "still running" if rc is None else f"exited with code {rc}"
        # Snapshot the deques first — the stderr drain thread may still be appending
        # concurrently, and iterating a deque mid-mutation raises in CPython.
        stderr_tail = list(self._stderr_tail)
        stdout_tail = list(self._stdout_tail)
        lines = [
            f"ht argv : {' '.join(self._argv) if self._argv else '(unknown)'}",
            f"ht state: {status}",
        ]
        if stderr_tail:
            lines.append("ht stderr (last lines):")
            lines += [f"  {ln}" for ln in stderr_tail]
        else:
            lines.append("ht stderr: (empty)")
        if stdout_tail:
            lines.append("ht stdout (last lines seen):")
            lines += [f"  {ln}" for ln in stdout_tail]
        return "\n".join(lines)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            if self._proc.stdin is not None:
                self._proc.stdin.close()
        finally:
            try:
                self._proc.terminate()
            except ProcessLookupError:
                pass


class LimaBackend(Backend):
    """Real :class:`Backend` that drives ``limactl`` (QEMU/KVM on Linux).

    Args:
        limactl: path/name of the limactl executable (default :data:`LIMACTL`).
        ht_binary: name of the in-guest headless-terminal binary used as the
            fallback when no host-side ht is available (default :data:`HT_BINARY`).
    """

    def __init__(self, limactl: str = LIMACTL, ht_binary: str = HT_BINARY) -> None:
        self._limactl = limactl
        # In-guest fallback name on PATH (used when the host has no shippable ht).
        self._ht = ht_binary
        # HOST-side ht the broker ships; copied into the guest on demand by
        # open_capture so capture works on any guest, even a deny-locked one.
        self._host_ht = _host_ht_path()

    # ── one lifecycle shell-out helper (raises on nonzero) ───────────────────
    def _run(
        self, argv: list[str], *, stdin: str | None = None, stream: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Run a ``limactl`` lifecycle command, raising on a nonzero exit.

        ``argv`` is the full ``limactl`` argument vector (without the executable,
        which is prepended here). Used for every verb whose failure is a real
        backend error — i.e. everything **except** :meth:`exec`, which returns
        the guest code instead.

        When ``stream`` is set, ``limactl``'s stderr is INHERITED (not captured)
        so its progress — image download, ``Starting QEMU``, ``waiting for ssh`` —
        flows live to our stderr. A slow first-run ``create``/``start`` is
        otherwise a silent multi-minute wait that looks hung. stdout is still
        captured; on failure the streamed lines above are the detail.
        """
        full = [self._limactl, *argv]
        if stream:
            proc = subprocess.run(full, input=stdin, stdout=subprocess.PIPE, stderr=None, text=True)
        else:
            proc = subprocess.run(full, input=stdin, capture_output=True, text=True)
        if proc.returncode != 0:
            cmd = " ".join(full)
            detail = "(see the limactl output above)" if stream else (proc.stderr or "").strip()
            raise BackendError(f"{cmd} failed (exit {proc.returncode}): {detail}")
        return proc

    # ── lifecycle ────────────────────────────────────────────────────────────
    def create(self, name: str, template_yaml: str) -> None:
        # `limactl create --name N -` reads the template from stdin. Stream so
        # image registration/download progress is visible, not a silent wait.
        self._run(["create", "--name", name, "-"], stdin=template_yaml, stream=True)

    def start(self, name: str) -> None:
        # `-y` (== --tty=false) for non-interactive/CI boot. The first start of a
        # fresh instance downloads the base image and boots QEMU — minutes, not
        # seconds — so announce it up front and stream limactl's live progress.
        print(
            f"lince-lab: starting VM {name!r} — first run downloads the base image "
            "and boots QEMU; this can take several minutes…",
            file=sys.stderr,
            flush=True,
        )
        self._run(["start", name, "-y"], stream=True)

    def stop(self, name: str, force: bool = False) -> None:
        argv = ["stop", name]
        if force:
            argv.append("-f")
        self._run(argv)

    def delete(self, name: str, force: bool = False) -> None:
        argv = ["delete", name]
        if force:
            argv.append("-f")
        self._run(argv)

    def status(self, name: str) -> VmState:
        # `limactl list N --json` emits zero records when the instance is absent.
        records = self._list_json([name])
        if not records:
            return VmState(name=name, status=VmStatus.ABSENT, snapshots=[])
        rec = records[0]
        return VmState(
            name=str(rec.get("name", name)),
            status=_map_status(str(rec.get("status", ""))),
            snapshots=self._safe_snapshot_list(name),
        )

    def list(self) -> list[VmState]:
        states: list[VmState] = []
        for rec in self._list_json([]):
            nm = str(rec.get("name", ""))
            states.append(
                VmState(
                    name=nm,
                    status=_map_status(str(rec.get("status", ""))),
                    snapshots=self._safe_snapshot_list(nm),
                )
            )
        return states

    def _list_json(self, names: list[str]) -> list[dict]:
        """Run ``limactl list [names...] --json`` → parsed list of records.

        Lima emits one JSON object per line (JSON-lines), not a JSON array, so we
        parse line-by-line. An absent instance yields no lines.
        """
        proc = self._run(["list", *names, "--json"])
        records: list[dict] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
        return records

    def _safe_snapshot_list(self, name: str) -> list[str]:
        """Best-effort snapshot tags for ``name`` (empty if listing fails)."""
        try:
            return self.snapshot_list(name)
        except BackendError:
            return []

    # ── exec / files (exit code propagates, never raises on guest nonzero) ────
    def exec(
        self,
        name: str,
        argv: list[str],
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> ExecResult:
        cmd = [self._limactl, "shell"]
        if workdir is not None:
            cmd += ["--workdir", workdir]
        cmd += [name, "--", *argv]
        # `env` is injected as a leading `env K=V ...` prefix inside the guest so
        # it never relies on the host environment leaking through limactl.
        if env:
            prefix = ["env"] + [f"{k}={v}" for k, v in env.items()]
            cmd = cmd[: cmd.index("--") + 1] + prefix + argv
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # CRITICAL: return the guest exit code verbatim; do NOT raise. limactl
        # propagates the guest command's exit code, which is the bisect signal.
        return ExecResult(exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)

    def copy_in(self, name: str, host_path: str, guest_path: str, recursive: bool = False) -> None:
        argv = ["copy"]
        if recursive:
            argv.append("-r")
        argv += [host_path, f"{name}:{guest_path}"]
        self._run(argv)

    def copy_out(self, name: str, guest_path: str, host_path: str, recursive: bool = False) -> None:
        argv = ["copy"]
        if recursive:
            argv.append("-r")
        argv += [f"{name}:{guest_path}", host_path]
        self._run(argv)

    # ── snapshots ────────────────────────────────────────────────────────────
    def snapshot_create(self, name: str, tag: str) -> None:
        self._run(["snapshot", "create", name, "--tag", tag])

    def snapshot_apply(self, name: str, tag: str) -> None:
        self._run(["snapshot", "apply", name, "--tag", tag])

    def snapshot_delete(self, name: str, tag: str) -> None:
        self._run(["snapshot", "delete", name, "--tag", tag])

    def snapshot_list(self, name: str) -> list[str]:
        proc = self._run(["snapshot", "list", name])
        return self._parse_snapshot_list(proc.stdout)

    @staticmethod
    def _parse_snapshot_list(stdout: str) -> list[str]:
        """Parse ``limactl snapshot list`` output into a list of snapshot tags.

        The QEMU backend surfaces qemu's snapshot table, whose columns are
        ``ID  TAG  VM SIZE  DATE  VM CLOCK`` — the tag is the **second** column,
        under a ``TAG`` header (usually preceded by a ``List of snapshots ...``
        line). We locate the ``TAG`` header column and read that column from each
        following row. If no recognizable header is found we fall back to
        one-tag-per-line (first field), tolerating a simpler ``TAG``-then-tags
        layout.
        """
        lines = [ln for ln in stdout.splitlines() if ln.strip()]
        for i, line in enumerate(lines):
            upper = [f.upper() for f in line.split()]
            if "TAG" in upper:
                tag_col = upper.index("TAG")
                tags: list[str] = []
                for row in lines[i + 1 :]:
                    cols = row.split()
                    if len(cols) > tag_col:
                        tags.append(cols[tag_col])
                return tags
        # No header row → assume one tag per line (first field).
        return [line.split()[0] for line in lines]

    # ── capture ──────────────────────────────────────────────────────────────
    def open_capture(self, name: str, argv: list[str], cols: int, rows: int) -> CaptureChannel:
        # `ht` ships HOST-SIDE. If the host binary exists on disk, copy it into the
        # guest first (and make it executable) so capture works on ANY guest — even
        # a deny-locked one that can't fetch ht itself. Copying our own disposable
        # capture driver into a disposable guest does NOT widen the agent's host
        # access. If no host ht is present, fall back to a bare `ht` on guest PATH.
        if os.path.isfile(self._host_ht):
            self.copy_in(name, self._host_ht, GUEST_HT_PATH)
            self._run(["shell", name, "--", "chmod", "+x", GUEST_HT_PATH])
            guest_ht = GUEST_HT_PATH
        else:
            guest_ht = self._ht
        # Spawn `ht` inside the guest, wrapping `argv` at a fixed grid, streaming
        # init/output/snapshot events over stdout; drive it over stdin.
        cmd = [
            self._limactl,
            "shell",
            name,
            "--",
            guest_ht,
            "--size",
            f"{cols}x{rows}",
            "--subscribe",
            "init,output,snapshot",
            "--",
            *argv,
        ]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        return LimaCaptureChannel(proc, argv=cmd)
