#!/usr/bin/env python3
"""Tests for `lince-config apply` / `templates` (#207).

Run with:
    python3 scripts/tests/test_apply.py
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import tempfile
import tomllib
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_lince_config():
    path = REPO_ROOT / "lince-config" / "lince-config"
    spec = importlib.util.spec_from_loader(
        "lince_config_apply_test",
        importlib.machinery.SourceFileLoader("lince_config_apply_test", str(path)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ApplyTestCase(unittest.TestCase):
    def setUp(self):
        self.lc = load_lince_config()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.lince_cfg = root / "lince" / "lince.toml"
        self.lc.LINCE_REGISTRY_DIRS = [REPO_ROOT / "registry.d"]
        self.lc.LINCE_CONFIG_PATH = self.lince_cfg
        self.lc.SANDBOX_CONFIG_PATH = root / "sandbox-config.toml"
        self.lc.DASHBOARD_CONFIG_PATH = root / "dashboard-config.toml"
        self.lc.SANDBOX_PROFILES_DIR = root / "profiles"
        self.lc.NONO_PROFILES_DIR = root / "nono-profiles"

    def tearDown(self):
        self.tmp.cleanup()

    def apply(self, combo, project=None, dry_run=False, force_v2=False):
        args = types.SimpleNamespace(
            combo=combo, project=str(project) if project else None,
            dry_run=dry_run, force_v2=force_v2,
        )
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.lc.cmd_apply(args)
        return rc, out.getvalue(), err.getvalue()

    # ── happy path ───────────────────────────────────────────────────────

    def test_fresh_machine_one_command(self):
        rc, out, err = self.apply("claude+normal+anthropic")
        self.assertEqual(rc, 0, err)
        parsed = tomllib.loads(self.lince_cfg.read_text())
        self.assertEqual(parsed["version"], "2.0")
        self.assertEqual(parsed["agents"]["claude"]["level"], "normal")
        self.assertEqual(parsed["agents"]["claude"]["provider"], "anthropic")
        # the result resolves: level/provider visible, origin = user
        view, error = self.lc.build_resolved_view()
        self.assertIsNone(error)
        self.assertEqual(view["agents"]["claude"]["level"], "normal")
        self.assertEqual(view["agents"]["claude"]["provider"], "anthropic")
        # the written file passes the validator with zero issues
        issues = []
        self.lc.schema_validate(parsed, self.lc.LINCE_SCHEMA, "", issues)
        self.assertEqual(issues, [])

    def test_reapply_is_noop(self):
        self.apply("claude+paranoid")
        before = self.lince_cfg.read_text()
        rc, out, _ = self.apply("claude+paranoid")
        self.assertEqual(rc, 0)
        self.assertIn("no-op", out)
        self.assertEqual(self.lince_cfg.read_text(), before)

    def test_order_of_level_and_provider_is_free(self):
        rc, _, err = self.apply("codex+openai+permissive")
        self.assertEqual(rc, 0, err)
        parsed = tomllib.loads(self.lince_cfg.read_text())
        self.assertEqual(parsed["agents"]["codex"]["level"], "permissive")
        self.assertEqual(parsed["agents"]["codex"]["provider"], "openai")

    def test_dry_run_writes_nothing(self):
        rc, out, _ = self.apply("claude+paranoid", dry_run=True)
        self.assertEqual(rc, 0)
        self.assertIn("+level = \"paranoid\"", out)
        self.assertFalse(self.lince_cfg.exists())

    def test_project_overlay(self):
        project = Path(self.tmp.name) / "proj"
        project.mkdir()
        rc, _, err = self.apply("claude+paranoid", project=project)
        self.assertEqual(rc, 0, err)
        overlay = project / ".lince" / "lince.toml"
        parsed = tomllib.loads(overlay.read_text())
        self.assertEqual(parsed["agents"]["claude"]["level"], "paranoid")
        # overlays carry no version key (§2.4)
        self.assertNotIn("version", parsed)
        self.assertFalse(self.lince_cfg.exists())

    # ── failure modes (nothing written) ──────────────────────────────────

    def test_unknown_agent_fails_before_writing(self):
        rc, _, err = self.apply("nosuch+normal")
        self.assertEqual(rc, 1)
        self.assertIn("unknown agent", err)
        self.assertFalse(self.lince_cfg.exists())

    def test_unknown_token_fails_with_both_lists(self):
        rc, _, err = self.apply("claude+warpspeed")
        self.assertEqual(rc, 1)
        self.assertIn("neither an isolation level", err)
        self.assertFalse(self.lince_cfg.exists())

    def test_level_pin_respected(self):
        rc, _, err = self.apply("bash+paranoid")
        self.assertEqual(rc, 1)
        self.assertIn("only supports level(s): normal", err)

    def test_double_level_fails(self):
        rc, _, err = self.apply("claude+normal+paranoid")
        self.assertEqual(rc, 1)
        self.assertIn("two isolation levels", err)

    # ── the §5.2 v2-switch guard ─────────────────────────────────────────

    def test_legacy_intent_blocks_v2_switch(self):
        self.lc.SANDBOX_CONFIG_PATH.write_text(
            '[providers.vertex]\nenv = { CLOUD_ML_REGION = "us-east5" }\n',
            encoding="utf-8",
        )
        rc, _, err = self.apply("claude+normal")
        self.assertEqual(rc, 1)
        self.assertIn("force-v2", err)
        self.assertIn("vertex" if "vertex" in err else "providers", err)
        self.assertFalse(self.lince_cfg.exists())
        # explicit opt-in proceeds
        rc, _, err = self.apply("claude+normal", force_v2=True)
        self.assertEqual(rc, 0, err)
        self.assertTrue(self.lince_cfg.exists())

    def test_fresh_init_config_does_not_block(self):
        """A fresh `agent-sandbox init` config has no providers/agent
        overrides — apply must not demand --force-v2."""
        example = (REPO_ROOT / "sandbox" / "config.toml.example").read_text()
        self.lc.SANDBOX_CONFIG_PATH.write_text(example, encoding="utf-8")
        rc, _, err = self.apply("claude+normal")
        self.assertEqual(rc, 0, err)

    # ── enabled_agents (the quickstart selection mechanism) ─────────────

    def test_enabled_agents_filters_resolve(self):
        self.lince_cfg.parent.mkdir(parents=True)
        self.lince_cfg.write_text(
            'version = "2.0"\n[dashboard]\nenabled_agents = ["claude", "bash"]\n',
            encoding="utf-8",
        )
        view, error = self.lc.build_resolved_view()
        self.assertIsNone(error)
        self.assertEqual(sorted(view["agents"]), ["bash", "claude"])

    def test_custom_agents_always_visible(self):
        self.lince_cfg.parent.mkdir(parents=True)
        self.lince_cfg.write_text(
            'version = "2.0"\n'
            '[dashboard]\nenabled_agents = ["claude"]\n'
            '[agents.bob]\nbinary = "bob"\ndisplay_name = "Bob"\n'
            'short_label = "BOB"\ncolor = "magenta"\n',
            encoding="utf-8",
        )
        view, _ = self.lc.build_resolved_view()
        self.assertEqual(sorted(view["agents"]), ["bob", "claude"])


class TemplatesTestCase(unittest.TestCase):
    def test_templates_json(self):
        lc = load_lince_config()
        lc.LINCE_REGISTRY_DIRS = [REPO_ROOT / "registry.d"]
        args = types.SimpleNamespace(json=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = lc.cmd_templates(args)
        self.assertEqual(rc, 0)
        import json
        data = json.loads(out.getvalue())
        names = {a["name"] for a in data["agents"]}
        self.assertIn("claude", names)
        self.assertEqual(
            {lv["name"] for lv in data["levels"]} >= {"paranoid", "normal", "permissive"},
            True,
        )
        self.assertIn("anthropic", {p["name"] for p in data["providers"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
