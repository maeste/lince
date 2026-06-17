#!/usr/bin/env python3
"""Unit tests for :mod:`lince_lab.lima_backend` (blueprint §2).

These assert the EXACT ``limactl`` argv built for each :class:`LimaBackend`
method by mocking :mod:`subprocess` — no real VM/KVM is touched. They also pin
the two load-bearing behaviours:

* ``exec`` returns the mocked guest return code WITHOUT raising (the bisect
  signal), and
* a lifecycle verb raises :class:`~lince_lab.errors.BackendError` on a nonzero
  ``limactl`` exit.

Run with:
    python3 lince-lab/tests/test_lima_backend.py
"""

import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab.backend import VmStatus  # noqa: E402
from lince_lab.errors import BackendError  # noqa: E402
from lince_lab.lima_backend import (  # noqa: E402
    GUEST_HT_PATH,
    LimaBackend,
    LimaCaptureChannel,
)


def _ok(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    """Build a CompletedProcess stand-in for ``subprocess.run`` to return."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class LifecycleArgvTestCase(unittest.TestCase):
    """Assert the exact ``limactl`` argv for each lifecycle/file/snapshot verb."""

    def setUp(self) -> None:
        self.backend = LimaBackend()

    def _patch_run(self, result: subprocess.CompletedProcess) -> mock.MagicMock:
        patcher = mock.patch("lince_lab.lima_backend.subprocess.run", return_value=result)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def _argv(self, run: mock.MagicMock) -> list:
        """The first positional arg (the full argv list) of the last run call."""
        return run.call_args.args[0]

    def test_create_passes_template_on_stdin(self) -> None:
        run = self._patch_run(_ok())
        self.backend.create("lab", "images: []\n")
        self.assertEqual(self._argv(run), ["limactl", "create", "--name", "lab", "-"])
        # Template YAML must be fed on stdin via the `input` kwarg.
        self.assertEqual(run.call_args.kwargs["input"], "images: []\n")

    def test_start_is_non_interactive(self) -> None:
        run = self._patch_run(_ok())
        self.backend.start("lab")
        self.assertEqual(self._argv(run), ["limactl", "start", "lab", "-y"])

    def test_stop_plain_and_force(self) -> None:
        run = self._patch_run(_ok())
        self.backend.stop("lab")
        self.assertEqual(self._argv(run), ["limactl", "stop", "lab"])
        self.backend.stop("lab", force=True)
        self.assertEqual(self._argv(run), ["limactl", "stop", "lab", "-f"])

    def test_delete_plain_and_force(self) -> None:
        run = self._patch_run(_ok())
        self.backend.delete("lab")
        self.assertEqual(self._argv(run), ["limactl", "delete", "lab"])
        self.backend.delete("lab", force=True)
        self.assertEqual(self._argv(run), ["limactl", "delete", "lab", "-f"])

    def test_copy_in_uses_instance_colon_path_target(self) -> None:
        run = self._patch_run(_ok())
        self.backend.copy_in("lab", "./work", "/work", recursive=True)
        self.assertEqual(self._argv(run), ["limactl", "copy", "-r", "./work", "lab:/work"])

    def test_copy_in_non_recursive(self) -> None:
        run = self._patch_run(_ok())
        self.backend.copy_in("lab", "./f.txt", "/tmp/f.txt")
        self.assertEqual(self._argv(run), ["limactl", "copy", "./f.txt", "lab:/tmp/f.txt"])

    def test_copy_out_uses_instance_colon_path_source(self) -> None:
        run = self._patch_run(_ok())
        self.backend.copy_out("lab", "/etc/os-release", "./os-release")
        self.assertEqual(self._argv(run), ["limactl", "copy", "lab:/etc/os-release", "./os-release"])

    def test_snapshot_create(self) -> None:
        run = self._patch_run(_ok())
        self.backend.snapshot_create("lab", "base-clean")
        self.assertEqual(self._argv(run), ["limactl", "snapshot", "create", "lab", "--tag", "base-clean"])

    def test_snapshot_apply(self) -> None:
        run = self._patch_run(_ok())
        self.backend.snapshot_apply("lab", "base-clean")
        self.assertEqual(self._argv(run), ["limactl", "snapshot", "apply", "lab", "--tag", "base-clean"])

    def test_snapshot_delete(self) -> None:
        run = self._patch_run(_ok())
        self.backend.snapshot_delete("lab", "base-clean")
        self.assertEqual(self._argv(run), ["limactl", "snapshot", "delete", "lab", "--tag", "base-clean"])

    def test_snapshot_list_parses_tags_and_skips_header(self) -> None:
        run = self._patch_run(_ok(stdout="TAG\nbase-clean\ncandidate-2\n"))
        tags = self.backend.snapshot_list("lab")
        self.assertEqual(self._argv(run), ["limactl", "snapshot", "list", "lab"])
        self.assertEqual(tags, ["base-clean", "candidate-2"])

    def test_snapshot_list_parses_qemu_table_tag_column(self) -> None:
        # The real QEMU backend prints qemu's table: the tag is the 2nd column,
        # under a TAG header, after a "List of snapshots ..." preamble line.
        stdout = (
            "List of snapshots present on all disks:\n"
            "ID        TAG          VM SIZE    DATE                  VM CLOCK\n"
            "1         base         0 B        2026-06-16 09:00:00   00:00:00.000\n"
            "2         other        0 B        2026-06-16 09:01:00   00:00:00.000\n"
        )
        self.assertEqual(LimaBackend._parse_snapshot_list(stdout), ["base", "other"])


class StatusListTestCase(unittest.TestCase):
    """Assert `limactl list --json` argv + parsing into VmState."""

    def setUp(self) -> None:
        self.backend = LimaBackend()

    def test_status_present_running(self) -> None:
        record = {"name": "lab", "status": "Running"}
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            side_effect=[
                _ok(stdout=json.dumps(record) + "\n"),  # list lab --json
                _ok(stdout="TAG\nbase\n"),  # snapshot list lab
            ],
        ) as run:
            state = self.backend.status("lab")
        # First call is the list --json with the instance name.
        self.assertEqual(run.call_args_list[0].args[0], ["limactl", "list", "lab", "--json"])
        self.assertEqual(state.status, VmStatus.RUNNING)
        self.assertEqual(state.name, "lab")
        self.assertEqual(state.snapshots, ["base"])

    def test_status_absent_when_no_records(self) -> None:
        with mock.patch("lince_lab.lima_backend.subprocess.run", return_value=_ok(stdout="")) as run:
            state = self.backend.status("ghost")
        self.assertEqual(run.call_args.args[0], ["limactl", "list", "ghost", "--json"])
        self.assertEqual(state.status, VmStatus.ABSENT)
        self.assertEqual(state.snapshots, [])

    def test_list_all_parses_each_line(self) -> None:
        recs = [
            {"name": "a", "status": "Running"},
            {"name": "b", "status": "Stopped"},
        ]
        stdout = "\n".join(json.dumps(r) for r in recs) + "\n"
        # Every status() call after the list also triggers a snapshot list; return
        # an empty snapshot listing for those follow-ups.
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            side_effect=[_ok(stdout=stdout), _ok(stdout="TAG\n"), _ok(stdout="TAG\n")],
        ) as run:
            states = self.backend.list()
        self.assertEqual(run.call_args_list[0].args[0], ["limactl", "list", "--json"])
        self.assertEqual([s.name for s in states], ["a", "b"])
        self.assertEqual(states[0].status, VmStatus.RUNNING)
        self.assertEqual(states[1].status, VmStatus.STOPPED)


class ExecTestCase(unittest.TestCase):
    """exec must build `limactl shell ... -- argv` and return the code, never raise."""

    def setUp(self) -> None:
        self.backend = LimaBackend()

    def test_exec_argv_without_workdir(self) -> None:
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(stdout="hi", returncode=0),
        ) as run:
            result = self.backend.exec("lab", ["sh", "-c", "echo hi"])
        self.assertEqual(
            run.call_args.args[0],
            ["limactl", "shell", "lab", "--", "sh", "-c", "echo hi"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "hi")

    def test_exec_argv_with_workdir(self) -> None:
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(),
        ) as run:
            self.backend.exec("lab", ["./run-tests.sh"], workdir="/work")
        self.assertEqual(
            run.call_args.args[0],
            ["limactl", "shell", "--workdir", "/work", "lab", "--", "./run-tests.sh"],
        )

    def test_exec_injects_env_prefix_in_guest(self) -> None:
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(),
        ) as run:
            self.backend.exec("lab", ["make", "test"], env={"CI": "1"})
        self.assertEqual(
            run.call_args.args[0],
            ["limactl", "shell", "lab", "--", "env", "CI=1", "make", "test"],
        )

    def test_exec_returns_guest_nonzero_without_raising(self) -> None:
        # A failing guest command is DATA, not an error: exec must return the
        # code, never raise — this is the bisect signal.
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(stdout="", stderr="boom", returncode=1),
        ):
            result = self.backend.exec("lab", ["false"])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stderr, "boom")

    def test_exec_passes_timeout_through(self) -> None:
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(),
        ) as run:
            self.backend.exec("lab", ["sleep", "1"], timeout=5.0)
        self.assertEqual(run.call_args.kwargs["timeout"], 5.0)


class LifecycleFailureTestCase(unittest.TestCase):
    """A lifecycle verb must raise BackendError on a nonzero limactl exit."""

    def setUp(self) -> None:
        self.backend = LimaBackend()

    def test_start_raises_on_nonzero(self) -> None:
        # `start` STREAMS limactl's output live (so a slow first boot is not a
        # silent hang), so its stderr is inherited, not captured — the error names
        # the failed command + exit code and points to the streamed output above.
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(stderr="no such instance", returncode=1),
        ):
            with self.assertRaises(BackendError) as ctx:
                self.backend.start("lab")
        msg = str(ctx.exception)
        self.assertIn("limactl start lab -y failed", msg)
        self.assertIn("exit 1", msg)
        self.assertIn("see the limactl output", msg)

    def test_create_raises_on_nonzero(self) -> None:
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(stderr="bad template", returncode=2),
        ):
            with self.assertRaises(BackendError):
                self.backend.create("lab", "broken: [")

    def test_snapshot_apply_raises_on_nonzero(self) -> None:
        with mock.patch(
            "lince_lab.lima_backend.subprocess.run",
            return_value=_ok(stderr="no such tag", returncode=1),
        ):
            with self.assertRaises(BackendError):
                self.backend.snapshot_apply("lab", "missing")


class OpenCaptureTestCase(unittest.TestCase):
    """open_capture ships ht HOST-SIDE: copy it in, chmod +x, then spawn it.

    When a host ht binary exists (``$LINCE_LAB_HT`` → a real file), open_capture
    must (a) copy it to the guest ``/tmp/lince-lab-ht``, (b) ``chmod +x`` it in the
    guest, and (c) spawn the in-guest ``/tmp/lince-lab-ht``. With NO host ht it
    falls back to the bare ``ht`` on the guest PATH and copies nothing.
    """

    def test_open_capture_copies_host_ht_and_spawns_guest_path(self) -> None:
        # Point LINCE_LAB_HT at a real tempfile so the host ht "exists" on disk.
        with tempfile.NamedTemporaryFile(suffix="-ht") as host_ht:
            host_ht.write(b"#!/bin/sh\n")
            host_ht.flush()
            fake_proc = mock.MagicMock(spec=subprocess.Popen)
            fake_proc.stdout = None  # no reader/drain threads in this argv-only assertion
            fake_proc.stderr = None
            with mock.patch.dict(os.environ, {"LINCE_LAB_HT": host_ht.name}, clear=False):
                with mock.patch(
                    "lince_lab.lima_backend.subprocess.run",
                    return_value=_ok(),
                ) as run, mock.patch(
                    "lince_lab.lima_backend.subprocess.Popen",
                    return_value=fake_proc,
                ) as popen:
                    backend = LimaBackend()
                    channel = backend.open_capture("lab", ["./my-tui"], cols=80, rows=24)

        # (a) the host ht is copied to the guest /tmp/lince-lab-ht via limactl copy.
        copy_argv = run.call_args_list[0].args[0]
        self.assertEqual(copy_argv, ["limactl", "copy", host_ht.name, f"lab:{GUEST_HT_PATH}"])
        # (b) chmod +x runs in the guest.
        chmod_argv = run.call_args_list[1].args[0]
        self.assertEqual(chmod_argv, ["limactl", "shell", "lab", "--", "chmod", "+x", GUEST_HT_PATH])
        # (c) the ht process is spawned with the in-guest path + grid + subscribe.
        self.assertEqual(
            popen.call_args.args[0],
            [
                "limactl",
                "shell",
                "lab",
                "--",
                GUEST_HT_PATH,
                "--size",
                "80x24",
                "--subscribe",
                "init,output,snapshot",
                "--",
                "./my-tui",
            ],
        )
        self.assertIsInstance(channel, LimaCaptureChannel)
        # The spawn argv is recorded on the channel so diagnostics() can report it.
        self.assertEqual(channel._argv, popen.call_args.args[0])

    def test_open_capture_falls_back_to_bare_ht_without_host_binary(self) -> None:
        # No host ht: LINCE_LAB_HT points nowhere and no share binary exists.
        missing = str(pathlib.Path(tempfile.gettempdir()) / "lince-lab-no-such-ht-binary")
        self.assertFalse(os.path.exists(missing))
        fake_proc = mock.MagicMock(spec=subprocess.Popen)
        fake_proc.stdout = None  # no reader/drain threads in this argv-only assertion
        fake_proc.stderr = None
        with mock.patch.dict(os.environ, {"LINCE_LAB_HT": missing}, clear=False):
            with mock.patch(
                "lince_lab.lima_backend.subprocess.run",
                return_value=_ok(),
            ) as run, mock.patch(
                "lince_lab.lima_backend.subprocess.Popen",
                return_value=fake_proc,
            ) as popen:
                backend = LimaBackend()
                channel = backend.open_capture("lab", ["./my-tui"], cols=80, rows=24)
        # No copy_in / chmod when there is no host ht to ship.
        run.assert_not_called()
        # Spawns the bare `ht` on the guest PATH.
        self.assertEqual(
            popen.call_args.args[0],
            [
                "limactl",
                "shell",
                "lab",
                "--",
                "ht",
                "--size",
                "80x24",
                "--subscribe",
                "init,output,snapshot",
                "--",
                "./my-tui",
            ],
        )
        self.assertIsInstance(channel, LimaCaptureChannel)


class CaptureChannelTestCase(unittest.TestCase):
    """LimaCaptureChannel framing over a fake Popen's stdio pipes."""

    def _make_channel(self, lines: list[str]) -> tuple[LimaCaptureChannel, mock.MagicMock]:
        proc = mock.MagicMock(spec=subprocess.Popen)
        proc.stdin = mock.MagicMock()
        proc.stdout = mock.MagicMock()
        proc.stdout.readline.side_effect = lines
        # No stderr stream → no drain thread (these cases test stdout framing only).
        proc.stderr = None
        proc.poll.return_value = None
        return LimaCaptureChannel(proc), proc

    def test_send_line_writes_json_with_newline(self) -> None:
        channel, proc = self._make_channel([])
        channel.send_line({"type": "takeSnapshot"})
        proc.stdin.write.assert_called_once_with('{"type": "takeSnapshot"}\n')
        proc.stdin.flush.assert_called_once()

    def test_read_line_parses_json_event(self) -> None:
        channel, _ = self._make_channel(['{"type": "output", "data": {"seq": "x"}}\n'])
        event = channel.read_line(deadline=9e18)
        self.assertEqual(event, {"type": "output", "data": {"seq": "x"}})

    def test_read_line_returns_none_on_eof(self) -> None:
        channel, proc = self._make_channel([""])
        proc.poll.return_value = 0  # process has exited
        event = channel.read_line(deadline=9e18)
        self.assertIsNone(event)

    def test_read_line_respects_deadline_when_alive_and_silent(self) -> None:
        # Regression: a long-lived ht that has gone quiet (no new events, no EOF)
        # must NOT make read_line block forever — the deadline has to bound the
        # wait. Model it with a real pipe whose WRITE end stays open: readline()
        # in the reader thread blocks (no data, no EOF), the queue stays empty.
        r_fd, w_fd = os.pipe()
        rf = os.fdopen(r_fd, "r")
        proc = mock.MagicMock(spec=subprocess.Popen)
        proc.stdin = mock.MagicMock()
        proc.stdout = rf
        proc.stderr = None
        proc.poll.return_value = None  # still alive
        channel = LimaCaptureChannel(proc)
        try:
            start = time.monotonic()
            result = channel.read_line(deadline=time.monotonic() + 0.2)
            elapsed = time.monotonic() - start
            self.assertIsNone(result)
            self.assertLess(elapsed, 2.0)  # bounded by the deadline, did not hang
        finally:
            os.close(w_fd)  # EOF → the reader thread unblocks and exits
            rf.close()
            channel.close()

    def test_close_terminates_process(self) -> None:
        channel, proc = self._make_channel([])
        channel.close()
        self.assertTrue(channel.closed)
        proc.terminate.assert_called_once()
        # Idempotent: a second close is a no-op.
        channel.close()
        proc.terminate.assert_called_once()


class CaptureDiagnosticsTestCase(unittest.TestCase):
    """diagnostics() must surface ht's argv, exit status, and stderr tail.

    This is the blind-spot fix: without draining ht's stderr a capture timeout
    reported only a bare deadline, hiding the real cause (e.g. ``ht: command not
    found`` in a guest with no ht). The drain runs on a daemon thread.
    """

    def _drained_channel(self, stderr_text: str, returncode: int, argv: list[str]) -> LimaCaptureChannel:
        proc = mock.MagicMock(spec=subprocess.Popen)
        proc.stdin = mock.MagicMock()
        proc.stdout = mock.MagicMock()
        proc.stdout.readline.side_effect = [""]
        proc.stderr = io.StringIO(stderr_text)
        proc.poll.return_value = returncode
        channel = LimaCaptureChannel(proc, argv=argv)
        # The StringIO is finite, so the drain thread finishes promptly; join it.
        if channel._stderr_thread is not None:
            channel._stderr_thread.join(timeout=2.0)
        return channel

    def test_diagnostics_reports_argv_exit_and_stderr(self) -> None:
        argv = ["limactl", "shell", "lab", "--", "ht", "--size", "80x24", "--", "./tui"]
        channel = self._drained_channel("ht: command not found\n", returncode=127, argv=argv)
        diag = channel.diagnostics()
        self.assertIn("ht: command not found", diag)
        self.assertIn("exited with code 127", diag)
        self.assertIn("./tui", diag)  # the argv is echoed for context

    def test_diagnostics_notes_still_running_with_empty_stderr(self) -> None:
        proc = mock.MagicMock(spec=subprocess.Popen)
        proc.stdin = mock.MagicMock()
        proc.stdout = None  # diagnostics-only: no reader thread
        proc.stderr = None
        proc.poll.return_value = None  # still alive
        channel = LimaCaptureChannel(proc, argv=["ht"])
        diag = channel.diagnostics()
        self.assertIn("still running", diag)
        self.assertIn("(empty)", diag)


if __name__ == "__main__":
    unittest.main(verbosity=2)
