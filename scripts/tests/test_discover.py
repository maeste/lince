#!/usr/bin/env python3
"""Tests for `lince-config discover` (#208).

Run with:
    python3 scripts/tests/test_discover.py
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import tempfile
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_lince_config():
    path = REPO_ROOT / "lince-config" / "lince-config"
    spec = importlib.util.spec_from_loader(
        "lince_config_discover_test",
        importlib.machinery.SourceFileLoader("lince_config_discover_test", str(path)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DiscoverTestCase(unittest.TestCase):
    def setUp(self):
        self.lc = load_lince_config()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin_dir = root / "bin"
        self.bin_dir.mkdir()
        self.lc.LINCE_REGISTRY_DIRS = [REPO_ROOT / "registry.d"]
        self.lc.LINCE_CONFIG_PATH = root / "lince" / "lince.toml"
        self.lc.SANDBOX_CONFIG_PATH = root / "sandbox-config.toml"
        self.lc.DASHBOARD_CONFIG_PATH = root / "dashboard-config.toml"
        self.lc.SANDBOX_PROFILES_DIR = root / "profiles"
        self.lc.NONO_PROFILES_DIR = root / "nono-profiles"
        self._old_which = shutil.which
        self._old_env = dict(os.environ)
        # Hermetic host: only the binaries we fake exist; no provider keys.
        for var in list(os.environ):
            if var.endswith(("_API_KEY", "_TOKEN")) or var.startswith("AWS_"):
                os.environ.pop(var, None)

    def tearDown(self):
        shutil.which = self._old_which
        os.environ.clear()
        os.environ.update(self._old_env)
        self.tmp.cleanup()

    def fake_binaries(self, *names):
        for name in names:
            target = self.bin_dir / name
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o755)

        def which(cmd, *a, **kw):
            candidate = self.bin_dir / cmd
            return str(candidate) if candidate.is_file() else None

        shutil.which = which

    def discover(self):
        args = types.SimpleNamespace(json=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = self.lc.cmd_discover(args)
        self.assertEqual(rc, 0)
        return json.loads(out.getvalue())

    def test_exactly_installed_agents_proposed(self):
        """Acceptance: claude + codex installed → exactly those two agent
        templates, with valid absolute paths."""
        self.fake_binaries("claude", "codex")
        data = self.discover()
        self.assertEqual([a["name"] for a in data["agents"]], ["claude", "codex"])
        for agent in data["agents"]:
            self.assertTrue(Path(agent["path"]).is_absolute())
            self.assertTrue(Path(agent["path"]).is_file())
        self.assertEqual(data["suggestions"], [
            "lince-config apply claude+normal",
            "lince-config apply codex+normal",
        ])

    def test_shells_never_suggested(self):
        self.fake_binaries("bash", "zsh", "fish", "claude")
        data = self.discover()
        self.assertEqual([a["name"] for a in data["agents"]], ["claude"])
        self.assertEqual([s["name"] for s in data["shells"]], ["bash", "fish", "zsh"])
        self.assertEqual(len(data["suggestions"]), 1)

    def test_provider_added_when_credentials_detected(self):
        self.fake_binaries("claude")
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        data = self.discover()
        self.assertIn("anthropic", {p["name"] for p in data["providers"]})
        self.assertEqual(data["suggestions"],
                         ["lince-config apply claude+normal+anthropic"])

    def test_all_emitted_paths_are_absolute(self):
        """The #125 bug class: discovery must never emit relative paths."""
        self.fake_binaries("claude", "node", "cargo")
        data = self.discover()
        for agent in data["agents"]:
            self.assertTrue(Path(agent["path"]).is_absolute())
        for tool in data["toolchains"]:
            self.assertTrue(Path(tool["path"]).is_absolute())
        for path in data["paths"].values():
            self.assertTrue(Path(path).is_absolute())
            self.assertTrue(Path(path).is_dir())

    def test_suggestions_apply_cleanly(self):
        """Acceptance: suggestions always pass validation when applied."""
        self.fake_binaries("claude", "codex")
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        data = self.discover()
        for line in data["suggestions"]:
            combo = line.split()[-1]
            args = types.SimpleNamespace(combo=combo, project=None,
                                         dry_run=False, force_v2=False)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = self.lc.cmd_apply(args)
            self.assertEqual(rc, 0, f"{combo}: {err.getvalue()}")
        # and the resulting file validates
        issues = []
        import tomllib
        parsed = tomllib.loads(self.lc.LINCE_CONFIG_PATH.read_text())
        self.lc.schema_validate(parsed, self.lc.LINCE_SCHEMA, "", issues)
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
