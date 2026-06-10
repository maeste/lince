#!/usr/bin/env python3
"""Single-source guard for the embedded default sandbox config (#205).

`agent-sandbox init` writes the embedded `_DEFAULT_CONFIG`; the shipped
`sandbox/config.toml.example` documents it. The two had drifted (legacy
`default_profile` / `[profiles.*]` spelling in the embedded copy, `backend`
key missing from the example). This suite pins them byte-identical and
asserts a fresh init is warning-free.

Run with:
    python3 scripts/tests/test_default_config.py
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_module(rel_path: str, name: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, str(path))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDefaultConfigSingleSource(unittest.TestCase):
    def setUp(self):
        self.sandbox = load_module("sandbox/agent-sandbox", "agent_sandbox_dc_test")
        self.example = (REPO_ROOT / "sandbox" / "config.toml.example").read_text(encoding="utf-8")

    def test_embedded_equals_shipped_example(self):
        self.assertEqual(
            self.sandbox._DEFAULT_CONFIG, self.example,
            "_DEFAULT_CONFIG and sandbox/config.toml.example diverged — "
            "they are one artifact (#205); copy the example into the embedded string",
        )

    def test_default_config_uses_canonical_spelling(self):
        parsed = tomllib.loads(self.sandbox._DEFAULT_CONFIG)
        self.assertIn("default_provider", parsed["sandbox"])
        self.assertNotIn("default_profile", parsed["sandbox"])
        self.assertNotIn("profiles", parsed)

    def test_fresh_init_triggers_no_legacy_warning(self):
        """resolve_providers on a fresh config must not fire the
        _warn_legacy_profiles_once deprecation (the original #205 bug)."""
        parsed = tomllib.loads(self.sandbox._DEFAULT_CONFIG)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            for agent in ("claude", "codex", "gemini"):
                self.sandbox.resolve_providers(parsed, agent)
        self.assertFalse(self.sandbox._legacy_profiles_warned)
        self.assertEqual(stderr.getvalue(), "")

    def test_default_config_passes_schema_validation_clean(self):
        """Zero errors AND zero warnings against the published schema (#203)."""
        lc = load_module("lince-config/lince-config", "lince_config_dc_test")
        parsed = tomllib.loads(self.sandbox._DEFAULT_CONFIG)
        issues = lc.schema_validate(parsed, lc.SANDBOX_CONFIG_SCHEMA, "", [])
        self.assertEqual(issues, [], f"fresh init config has schema issues: {issues}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
