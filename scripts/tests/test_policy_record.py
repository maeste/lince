#!/usr/bin/env python3
"""Tests for the effective-policy attestation record (#221, design §4.3.1).

Run with:
    python3 scripts/tests/test_policy_record.py
"""

import importlib.machinery
import importlib.util
import io
import json
import contextlib
import os
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_agent_sandbox():
    path = REPO_ROOT / "sandbox" / "agent-sandbox"
    spec = importlib.util.spec_from_loader(
        "agent_sandbox_policy_test",
        importlib.machinery.SourceFileLoader("agent_sandbox_policy_test", str(path)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = load_agent_sandbox()


class TestRecordShape(unittest.TestCase):
    def record(self, **overrides):
        kwargs = dict(
            backend="bwrap",
            agent_name="claude",
            agent_id="claude-1",
            level="paranoid",
            requested_fs="bwrap bind mounts",
            requested_net="loopback-only via credential proxy (netns --unshare-net)",
            fs_enforced=True,
            net_enforced=True,
            bwrap_args_digest="abc123",
        )
        kwargs.update(overrides)
        return MOD.build_policy_record(**kwargs)

    def test_full_record_fields(self):
        rec = self.record()
        for field in (
            "schema", "agent", "agent_id", "backend", "requested",
            "landlock_abi", "fs_enforced", "net_enforced", "net_limitation",
            "bwrap_args_digest", "profile_digest", "helper_version",
            "helper_digest", "applied_before_exec",
            "inherited_by_subprocesses", "degraded_reason", "written_at",
        ):
            self.assertIn(field, rec)
        self.assertEqual(rec["requested"]["level"], "paranoid")
        self.assertIsInstance(rec["landlock_abi"], int)
        self.assertGreaterEqual(rec["landlock_abi"], 0)
        json.dumps(rec)  # must be JSON-serializable

    def test_degraded_requires_reason(self):
        """I7: the degraded path can never be silent."""
        with self.assertRaises(ValueError):
            self.record(net_enforced=False)
        rec = self.record(net_enforced=False, degraded_reason="ABI < 4")
        self.assertEqual(rec["degraded_reason"], "ABI < 4")


class TestParanoidFailClosed(unittest.TestCase):
    def make(self, fs=True, net=True):
        return {
            "fs_enforced": fs,
            "net_enforced": net,
            "degraded_reason": None if (fs and net) else "test degradation",
        }

    def test_paranoid_with_full_enforcement_launches(self):
        MOD.enforce_paranoid_fail_closed("paranoid", self.make())  # no exit

    def test_paranoid_with_degraded_boundary_fails_closed(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                MOD.enforce_paranoid_fail_closed("paranoid", self.make(net=False))
        self.assertEqual(ctx.exception.code, 1)
        # the missing boundary is NAMED (I6/I7)
        self.assertIn("network boundary", stderr.getvalue())
        self.assertIn("fails closed", stderr.getvalue())

    def test_normal_level_may_degrade(self):
        MOD.enforce_paranoid_fail_closed("normal", self.make(net=False))  # no exit
        MOD.enforce_paranoid_fail_closed(None, self.make(fs=False))  # no exit


class TestRecordWrite(unittest.TestCase):
    def test_write_next_to_state_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("LINCE_STATUS_DIR")
            os.environ["LINCE_STATUS_DIR"] = tmp
            try:
                rec = {"schema": 1, "fs_enforced": True}
                MOD.write_policy_record("claude-7", rec)
                path = Path(tmp) / "claude-7.policy.json"
                self.assertTrue(path.is_file())
                self.assertEqual(json.loads(path.read_text()), rec)
                # single line (the dashboard poll cats it with tr -d '\n')
                self.assertEqual(path.read_text().count("\n"), 1)
            finally:
                if old is None:
                    del os.environ["LINCE_STATUS_DIR"]
                else:
                    os.environ["LINCE_STATUS_DIR"] = old

    def test_no_agent_id_is_a_noop(self):
        MOD.write_policy_record(None, {"schema": 1})  # must not raise


class TestLandlockProbe(unittest.TestCase):
    def test_probe_returns_nonnegative_int(self):
        abi = MOD.probe_landlock_abi()
        self.assertIsInstance(abi, int)
        self.assertGreaterEqual(abi, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
