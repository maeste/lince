#!/usr/bin/env python3
"""Broker protocol + round-trip tests (blueprint §3).

Two layers:

* **pure codec**: envelope encode/decode, request validation, and the unknown-verb
  → exit 64 mapping (no socket);
* **full round-trip over a REAL unix socket**: a :class:`BrokerServer` backed by
  ``FakeBackend`` runs in a background thread on a socket in a ``TemporaryDirectory``;
  a :class:`BrokerClient` drives it. Covered: ping liveness, a vm lifecycle +
  exec round-trip, a nonzero guest exit surfaced verbatim in the response,
  snapshot round-trip, a policy denial mapped to exit 13, and broker-unreachable
  (exit 69) when nothing is listening.

No VM, no KVM — the substrate is entirely the in-memory FakeBackend.

Run with:
    python3 lince-lab/tests/test_broker_protocol.py
"""

import pathlib
import sys
import tempfile
import threading
import time
import unittest

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab import protocol  # noqa: E402
from lince_lab.broker import BrokerServer  # noqa: E402
from lince_lab.client import BrokerClient  # noqa: E402
from lince_lab.errors import (  # noqa: E402
    BROKER_UNREACHABLE,
    POLICY_DENIED,
    UNKNOWN_VERB,
    BrokerUnreachable,
    DataError,
    LabError,
    UnknownVerb,
)
from lince_lab.backend import ExecResult  # noqa: E402
from lince_lab.fake_backend import FakeBackend  # noqa: E402

LAB_VM = "lince-lab-demo"


class CodecTests(unittest.TestCase):
    """Pure envelope codec + verb-whitelist behavior (no socket)."""

    def test_encode_decode_round_trip(self):
        req = protocol.make_request("vm.exec", {"name": LAB_VM, "argv": ["true"]})
        line = protocol.encode(req)
        self.assertTrue(line.endswith(b"\n"))
        decoded = protocol.decode(line)
        self.assertEqual(decoded, req)

    def test_encode_is_deterministic(self):
        a = protocol.encode({"v": 1, "id": "x", "verb": "ping", "args": {}})
        b = protocol.encode({"args": {}, "verb": "ping", "id": "x", "v": 1})
        self.assertEqual(a, b)

    def test_make_request_rejects_unknown_verb(self):
        with self.assertRaises(UnknownVerb) as exc:
            protocol.make_request("vm.evil")
        self.assertEqual(exc.exception.exit_code, UNKNOWN_VERB)

    def test_validate_request_unknown_verb_maps_to_64(self):
        envelope = {"v": 1, "id": "abc", "verb": "vm.evil", "args": {}}
        with self.assertRaises(UnknownVerb) as exc:
            protocol.validate_request(envelope)
        self.assertEqual(exc.exception.exit_code, 64)

    def test_validate_request_bad_version(self):
        with self.assertRaises(DataError):
            protocol.validate_request({"v": 99, "id": "x", "verb": "ping", "args": {}})

    def test_decode_malformed_line(self):
        with self.assertRaises(DataError):
            protocol.decode(b"{not json}\n")

    def test_error_envelope_carries_exit(self):
        err = protocol.make_error("id1", "POLICY_DENIED", "nope", 13)
        self.assertFalse(err["ok"])
        self.assertEqual(err["error"]["exit"], 13)


class _ServerFixture(unittest.TestCase):
    """Starts a FakeBackend-backed BrokerServer on a real unix socket in a thread."""

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

    def _await_socket(self) -> None:
        """Block until the listening socket accepts a connection."""
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                with BrokerClient(self.sock_path, timeout=1.0) as client:
                    client.call("ping")
                return
            except BrokerUnreachable:
                time.sleep(0.01)
        self.fail("broker socket never came up")

    def client(self) -> BrokerClient:
        return BrokerClient(self.sock_path, timeout=2.0)


class RoundTripTests(_ServerFixture):
    """End-to-end CLI-side client → real socket → broker → FakeBackend."""

    def test_ping(self):
        with self.client() as c:
            result = c.call("ping")
        self.assertTrue(result["pong"])

    def test_vm_lifecycle_and_exec(self):
        with self.client() as c:
            c.call("vm.create", {"name": LAB_VM, "template_yaml": "ignored-by-policy"})
            c.call("vm.start", {"name": LAB_VM})
            # Register a passing command on the backend, then exec it.
            self.backend.on(LAB_VM, ["sh", "-c", "make test"], ExecResult(0, "ok", ""))
            result = c.call("vm.exec", {"name": LAB_VM, "argv": ["sh", "-c", "make test"]})
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "ok")

    def test_nonzero_exec_exit_surfaced(self):
        with self.client() as c:
            c.call("vm.create", {"name": LAB_VM})
            c.call("vm.start", {"name": LAB_VM})
            self.backend.on(LAB_VM, ["false"], ExecResult(1, "", "boom"))
            result = c.call("vm.exec", {"name": LAB_VM, "argv": ["false"]})
        # A failing guest command is data, not an error: the exit code rides the
        # successful response and is the oracle/bisect signal.
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["stderr"], "boom")

    def test_status_and_list(self):
        with self.client() as c:
            c.call("vm.create", {"name": LAB_VM})
            c.call("vm.start", {"name": LAB_VM})
            status = c.call("vm.status", {"name": LAB_VM})
            listing = c.call("vm.list", {})
        self.assertEqual(status["status"], "running")
        self.assertIn(LAB_VM, [s["name"] for s in listing])

    def test_snapshot_round_trip(self):
        with self.client() as c:
            c.call("vm.create", {"name": LAB_VM})
            c.call("vm.start", {"name": LAB_VM})
            c.call("snap.create", {"name": LAB_VM, "tag": "base-clean"})
            tags = c.call("snap.list", {"name": LAB_VM})
            c.call("snap.apply", {"name": LAB_VM, "tag": "base-clean"})
        self.assertIn("base-clean", tags["snapshots"])

    def test_unknown_verb_round_trip_is_64(self):
        # Bypass the client's local whitelist by putting a raw envelope on the wire.
        with self.client() as c:
            c.connect()
            raw = {"v": 1, "id": "x1", "verb": "vm.evil", "args": {}}
            c.send(raw)
            response = c.recv()
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["exit"], UNKNOWN_VERB)

    def test_policy_denial_is_13(self):
        with self.client() as c:
            with self.assertRaises(LabError) as exc:
                # Unprefixed VM name trips the §3.5 name-prefix guard.
                c.call("vm.start", {"name": "not-a-lab-vm"})
        self.assertEqual(exc.exception.exit_code, POLICY_DENIED)

    def test_template_forcing_drops_client_template(self):
        # The client template is stripped by policy; the broker stores its own.
        with self.client() as c:
            c.call("vm.create", {"name": LAB_VM, "template_yaml": "mounts: [/home]"})
        stored = self.backend.fs_of(LAB_VM)["/.lince-lab/template.yaml"].decode()
        self.assertNotIn("mounts", stored)


class UnreachableTests(unittest.TestCase):
    """A missing socket maps to BROKER_UNREACHABLE (exit 69)."""

    def test_missing_socket_is_69(self):
        with tempfile.TemporaryDirectory() as d:
            missing = str(pathlib.Path(d) / "nope.sock")
            with self.assertRaises(BrokerUnreachable) as exc:
                BrokerClient(missing, timeout=0.5).call("ping")
        self.assertEqual(exc.exception.exit_code, BROKER_UNREACHABLE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
