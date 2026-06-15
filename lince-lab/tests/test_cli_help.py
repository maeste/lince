#!/usr/bin/env python3
"""CLI structure + end-to-end tests for the ``lince-lab`` front-end (blueprint §4).

Two layers, neither of which needs a VM:

* **structure** — the no-extension CLI executable is loaded via
  :class:`importlib.machinery.SourceFileLoader` (the repo idiom, see
  ``scripts/tests/test_resolve.py``). We assert the top-level ``--help`` lists all
  five command groups, each ``<group> --help`` lists that group's verbs, and a
  no-argument invocation returns 1.

* **end-to-end** — an in-process :class:`BrokerServer` backed by ``FakeBackend``
  runs on a real unix socket in a ``TemporaryDirectory``; the CLI is then driven
  **as a subprocess** (``python3 lince-lab/lince-lab --socket <sock> ...``) to
  prove exit-code propagation (a fake ``exec`` returning 1 → the CLI exits 1) and
  a vm lifecycle round-trip. The broker is started in-process (not via
  ``lab broker start``) so the test can register exec handlers on its FakeBackend.

Run with:
    python3 lince-lab/tests/test_cli_help.py
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest

PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(PACKAGE_DIR))

from lince_lab.backend import ExecResult  # noqa: E402
from lince_lab.broker import BrokerServer  # noqa: E402
from lince_lab.client import BrokerClient  # noqa: E402
from lince_lab.errors import BrokerUnreachable  # noqa: E402
from lince_lab.fake_backend import FakeBackend  # noqa: E402

CLI_PATH = PACKAGE_DIR / "lince-lab"
GROUPS = ("vm", "run", "find", "watch", "lab")
GROUP_VERBS = {
    "vm": ("up", "down", "rm", "status", "list", "exec", "copy", "snapshot"),
    "run": ("validate", "recipe", "presets"),
    "find": ("bisect",),
    "watch": ("grab", "keys", "wait"),
    "lab": ("broker", "doctor", "version"),
}
LAB_VM = "lince-lab-clitest"


def load_cli_module():
    """Load the no-extension ``lince-lab`` executable as an importable module."""
    loader = importlib.machinery.SourceFileLoader("lince_lab_cli_under_test", str(CLI_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _help_text(cli, argv):
    """Return the ``--help`` stdout for ``argv`` (which ends in ``--help``)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        with contextlib.suppress(SystemExit):
            cli.main(argv)
    return buf.getvalue()


class CliStructureTests(unittest.TestCase):
    """The grouped, multi-level help surface (no socket, no VM)."""

    @classmethod
    def setUpClass(cls):
        cls.cli = load_cli_module()

    def test_top_level_help_lists_all_groups(self):
        text = _help_text(self.cli, ["--help"])
        for group in GROUPS:
            self.assertIn(group, text, f"top-level --help should mention group {group!r}")

    def test_each_group_help_lists_its_verbs(self):
        for group, verbs in GROUP_VERBS.items():
            text = _help_text(self.cli, [group, "--help"])
            for verb in verbs:
                self.assertIn(verb, text, f"`{group} --help` should list verb {verb!r}")

    def test_no_args_returns_1(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = self.cli.main([])
        self.assertEqual(rc, 1)

    def test_group_without_verb_returns_1(self):
        for group in GROUPS:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = self.cli.main([group])
            self.assertEqual(rc, 1, f"`{group}` with no verb should return 1")

    def test_build_parser_exposes_five_groups(self):
        parser = self.cli.build_parser()
        # The subparsers action holds the group choices.
        choices = set()
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                choices.update(action.choices.keys())
        for group in GROUPS:
            self.assertIn(group, choices)


class CliEndToEndTests(unittest.TestCase):
    """CLI subprocess → real socket → in-process broker → FakeBackend."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sock_path = str(pathlib.Path(self.tmp.name) / "lince-lab.sock")
        self.backend = FakeBackend()
        self.server = BrokerServer(self.sock_path, self.backend, config={})
        self.server.bind()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self._await_socket()

    def tearDown(self):
        self.server.stop()
        self.thread.join(timeout=2.0)
        self.tmp.cleanup()

    def _await_socket(self):
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                with BrokerClient(self.sock_path, timeout=1.0) as client:
                    client.call("ping")
                return
            except BrokerUnreachable:
                time.sleep(0.01)
        self.fail("broker socket never came up")

    def _run_cli(self, *args):
        """Run the CLI executable as a subprocess against the test socket."""
        cmd = [sys.executable, str(CLI_PATH), "--socket", self.sock_path, *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    def test_broker_status_round_trip(self):
        proc = self._run_cli("lab", "broker", "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_vm_lifecycle_round_trip(self):
        self.assertEqual(self._run_cli("vm", "up", LAB_VM, "-q").returncode, 0)
        status = self._run_cli("vm", "status", LAB_VM, "--json")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("running", status.stdout)
        self.assertEqual(self._run_cli("vm", "down", LAB_VM, "-q").returncode, 0)
        self.assertEqual(self._run_cli("vm", "rm", LAB_VM, "-q").returncode, 0)

    def test_exec_propagates_guest_exit_code_1(self):
        self._run_cli("vm", "up", LAB_VM, "-q")
        # Register a guest command that exits 1; the CLI must exit 1 verbatim.
        self.backend.on(LAB_VM, ["false"], ExecResult(1, "", "boom"))
        proc = self._run_cli("vm", "exec", LAB_VM, "--", "false")
        self.assertEqual(proc.returncode, 1, f"expected guest exit 1, got {proc.returncode}: {proc.stderr}")
        self.assertIn("boom", proc.stderr)

    def test_exec_propagates_guest_exit_code_0(self):
        self._run_cli("vm", "up", LAB_VM, "-q")
        self.backend.on(LAB_VM, ["sh", "-c", "make test"], ExecResult(0, "ok\n", ""))
        proc = self._run_cli("vm", "exec", LAB_VM, "--", "sh", "-c", "make test")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ok", proc.stdout)

    def test_unreachable_socket_exits_69(self):
        missing = str(pathlib.Path(self.tmp.name) / "absent.sock")
        cmd = [sys.executable, str(CLI_PATH), "--socket", missing, "vm", "status", LAB_VM]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 69, proc.stderr)

    def test_unknown_verb_path_policy_prefix_denied_13(self):
        # A non-lab VM name trips the policy name-prefix guard (exit 13).
        proc = self._run_cli("vm", "status", "not-a-lab-vm")
        self.assertEqual(proc.returncode, 13, proc.stderr)

    def test_run_presets_is_local_and_lists_presets(self):
        proc = self._run_cli("run", "presets")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("quick", proc.stdout)
        self.assertIn("bisect", proc.stdout)
        self.assertIn("networked", proc.stdout)


if __name__ == "__main__":
    # Keep the CLI subprocesses from inheriting a stale LINCE_LAB_FAKE that would
    # make `lab broker start` paths diverge; the e2e broker is in-process here.
    os.environ.pop("LINCE_LAB_FAKE", None)
    unittest.main(verbosity=2)
