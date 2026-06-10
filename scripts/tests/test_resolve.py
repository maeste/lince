#!/usr/bin/env python3
"""Tests for `lince-config resolve --json` (#202, design §4.3).

Run with:
    python3 scripts/tests/test_resolve.py
"""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_lince_config_module():
    path = REPO_ROOT / "lince-config" / "lince-config"
    spec = importlib.util.spec_from_loader(
        "lince_config_resolve_test",
        importlib.machinery.SourceFileLoader("lince_config_resolve_test", str(path)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ResolveTestCase(unittest.TestCase):
    """Each test runs against the repo registry.d plus a scratch fake $HOME."""

    def setUp(self):
        self.lc = load_lince_config_module()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.sandbox_cfg = root / "agent-sandbox-config.toml"
        self.dashboard_cfg = root / "dashboard-config.toml"
        self.lince_cfg = root / "lince" / "lince.toml"
        self.profiles_dir = root / "profiles"
        self.nono_dir = root / "nono-profiles"
        # Redirect every filesystem touchpoint into the scratch dir.
        self.lc.LINCE_REGISTRY_DIRS = [REPO_ROOT / "registry.d"]
        self.lc.LINCE_CONFIG_PATH = self.lince_cfg
        self.lc.SANDBOX_CONFIG_PATH = self.sandbox_cfg
        self.lc.DASHBOARD_CONFIG_PATH = self.dashboard_cfg
        self.lc.SANDBOX_PROFILES_DIR = self.profiles_dir
        self.lc.NONO_PROFILES_DIR = self.nono_dir

    def tearDown(self):
        self.tmp.cleanup()

    def resolve(self, **kwargs):
        view, error = self.lc.build_resolved_view(**kwargs)
        self.assertIsNone(error, f"unexpected resolve error: {error}")
        return view

    # ── dual-read: registry only ────────────────────────────────────────

    def test_registry_only_view(self):
        view = self.resolve()
        self.assertEqual(view["guarantee"], "default-deny")
        self.assertIsNone(view["sources"]["user"])
        # all 10 shipped agents present
        self.assertIn("claude", view["agents"])
        self.assertIn("aider", view["agents"])
        claude = view["agents"]["claude"]
        self.assertEqual(claude["binary"], "claude")
        self.assertEqual(claude["level"], "normal")
        self.assertEqual(claude["origin"]["level"], "registry")
        self.assertEqual(claude["event_map"]["Stop"], "input")
        self.assertEqual(claude["dashboard"]["status_pipe_name"], "claude-status")
        # variant derivation incl. the codex exception
        self.assertEqual(view["agents"]["codex"]["variants"]["unsandboxed"]["command"],
                         ["codex", "--full-auto"])
        self.assertFalse(view["agents"]["codex"]["variants"]["unsandboxed"]["bwrap_conflict"])
        self.assertEqual(claude["variants"]["unsandboxed"]["command"], ["claude"])
        self.assertEqual(claude["variants"]["unsandboxed"]["short_label"], "CLU")
        # pi: provider_env = "all" expanded to $NAME self-refs (names only)
        pi_env = view["agents"]["pi"]["env"]
        self.assertEqual(pi_env.get("ANTHROPIC_API_KEY"), "$ANTHROPIC_API_KEY")
        self.assertNotIn("provider_env", pi_env)
        self.assertEqual(view["agents"]["pi"]["variants"]["unsandboxed"]["env"], pi_env)
        # shells pin their level set
        self.assertEqual(view["agents"]["bash"]["levels"], ["normal"])

    # ── dual-read: legacy user configs ──────────────────────────────────

    def test_legacy_sandbox_overrides_and_providers(self):
        self.sandbox_cfg.write_text(
            '[sandbox]\ndefault_provider = "vertex"\n'
            '[security]\nallow_domains = ["pypi.org"]\n'
            '[agents.claude]\ndefault_args = ["--continue"]\n'
            '[providers.vertex]\n'
            'env = { CLOUD_ML_REGION = "us-east5", ANTHROPIC_API_KEY = "sk-ant-LITERALSECRET123456" }\n'
            '[codex.providers.work]\nenv = { OPENAI_API_KEY = "$OPENAI_API_KEY" }\n',
            encoding="utf-8",
        )
        view = self.resolve()
        claude = view["agents"]["claude"]
        # per-field overlay: default_args replaced, everything else intact
        self.assertEqual(claude["default_args"], ["--continue"])
        self.assertEqual(claude["display_name"], "Claude Code")
        # provider attribution: vertex → claude, work → codex
        self.assertEqual(claude["providers_available"], ["vertex"])
        self.assertEqual(view["agents"]["codex"]["providers_available"], ["work"])
        # default provider + allowed hosts
        self.assertEqual(claude["provider"], "vertex")
        self.assertIn("pypi.org", claude["allowed_hosts_effective"])
        # secrets never cross (I4): the literal key is redacted to $NAME
        vertex = view["providers"]["vertex"]
        self.assertEqual(vertex["env"]["ANTHROPIC_API_KEY"], "$ANTHROPIC_API_KEY")
        self.assertEqual(vertex["env"]["CLOUD_ML_REGION"], "us-east5")
        self.assertTrue(vertex["available"])  # literal non-secret value configured
        self.assertNotIn("LITERALSECRET", json.dumps(view))

    def test_legacy_dashboard_custom_agent_and_level(self):
        self.dashboard_cfg.write_text(
            '[agents.claude]\nsandbox_level = "paranoid"\n'
            '[agents.bob]\n'
            'command = ["bob", "--go"]\n'
            'display_name = "Bob CLI"\nshort_label = "BOB"\ncolor = "magenta"\n'
            'pane_title_pattern = "bob"\nstatus_pipe_name = "lince-status"\n'
            'sandboxed = true\n'
            '[agents.bob.event_map]\nturn_end = "input"\n',
            encoding="utf-8",
        )
        view = self.resolve()
        self.assertEqual(view["agents"]["claude"]["level"], "paranoid")
        self.assertEqual(view["agents"]["claude"]["origin"]["level"], "user")
        bob = view["agents"]["bob"]
        self.assertEqual(bob["binary"], "bob")
        self.assertEqual(bob["display_name"], "Bob CLI")
        self.assertEqual(bob["event_map"], {"turn_end": "input"})
        # derived variant for free
        self.assertEqual(bob["variants"]["unsandboxed"]["short_label"], "BOU")
        self.assertEqual(bob["variants"]["unsandboxed"]["color"], "red")

    def test_malformed_custom_agent_fails_that_agent_only(self):
        self.dashboard_cfg.write_text(
            '[agents.broken]\ndisplay_name = "No Command"\n'
            '[agents.claude]\nsandbox_level = "paranoid"\n',
            encoding="utf-8",
        )
        view = self.resolve()
        self.assertNotIn("broken", view["agents"])
        self.assertIn("claude", view["agents"])
        self.assertTrue(any("broken" in w for w in view["warnings"]))

    def test_custom_level_discovery(self):
        self.profiles_dir.mkdir(parents=True)
        (self.profiles_dir / "claude-strict.toml").write_text("[security]\n", encoding="utf-8")
        (self.profiles_dir / "relaxed.toml").write_text("[security]\n", encoding="utf-8")
        (self.profiles_dir / "codex-hard.toml").write_text("[security]\n", encoding="utf-8")
        self.nono_dir.mkdir(parents=True)
        (self.nono_dir / "lince-claude-nstrict.json").write_text("{}", encoding="utf-8")
        view = self.resolve()
        claude = view["agents"]["claude"]
        self.assertEqual(
            claude["levels_by_backend"]["agent-sandbox"],
            ["paranoid", "normal", "permissive", "relaxed", "strict"],
        )
        self.assertIn("nstrict", claude["levels_by_backend"]["nono"])
        # codex-hard is codex's fragment, not an agnostic level for claude
        self.assertNotIn("codex-hard", claude["levels_by_backend"]["agent-sandbox"])
        self.assertIn("hard", view["agents"]["codex"]["levels_by_backend"]["agent-sandbox"])
        # shells keep their pin regardless of discovery
        self.assertEqual(view["agents"]["bash"]["levels"], ["normal"])

    # ── v2 path: lince.toml ─────────────────────────────────────────────

    def write_lince(self, content: str):
        self.lince_cfg.parent.mkdir(parents=True, exist_ok=True)
        self.lince_cfg.write_text(content, encoding="utf-8")

    def test_lince_toml_is_the_only_source(self):
        self.sandbox_cfg.write_text(
            '[agents.claude]\ndefault_args = ["--legacy-should-be-ignored"]\n',
            encoding="utf-8",
        )
        self.write_lince(
            'version = "2.0"\n'
            '[network]\nallowed_hosts = ["pypi.org"]\n'
            '[agents.claude]\nlevel = "paranoid"\nprovider = "anthropic"\n'
            'allowed_hosts = ["github.com"]\n'
        )
        view = self.resolve()
        claude = view["agents"]["claude"]
        # legacy file ignored entirely (§5.2 hard switch) + notice emitted
        self.assertEqual(claude["default_args"], ["--dangerously-skip-permissions"])
        self.assertTrue(any("migrate" in w for w in view["warnings"]))
        self.assertEqual(claude["level"], "paranoid")
        self.assertEqual(claude["origin"]["level"], "user")
        self.assertEqual(claude["provider"], "anthropic")
        hosts = claude["allowed_hosts_effective"]
        self.assertIn("pypi.org", hosts)
        self.assertIn("github.com", hosts)
        # provider hosts auto-added when selected
        self.assertIn("api.anthropic.com", hosts)

    def test_lince_toml_version_contract_fails_closed(self):
        self.write_lince('version = "2.9"\n')
        view, error = self.lc.build_resolved_view()
        self.assertIsNone(view)
        self.assertEqual(error["code"], "version")
        self.assertIn("newer lince", error["message"])

    def test_lince_missing_version_is_hard_error(self):
        self.write_lince('[network]\ndefault = "deny"\n')
        view, error = self.lc.build_resolved_view()
        self.assertIsNone(view)
        self.assertIn('Add: version = "2.0"', error["message"])

    def test_experimental_voids_guarantee(self):
        self.write_lince('version = "2.0"\n[experimental]\npermissive_network = true\n')
        view = self.resolve()
        self.assertEqual(view["guarantee"], "void:permissive_network")

    def test_experimental_reported_per_agent(self):
        """#210: per-agent hatches surface on that agent only; globals on all."""
        self.write_lince(
            'version = "2.0"\n'
            '[experimental]\nseatbelt_extra = "(allow file-write* (subpath \\"/opt\\"))"\n'
            '[experimental.agents.codex]\nraw_bwrap_args = ["--hostname", "x"]\n'
        )
        view = self.resolve()
        self.assertTrue(view["guarantee"].startswith("void:"))
        self.assertIn("seatbelt_extra", view["agents"]["claude"]["experimental"])
        self.assertNotIn("agents.codex.raw_bwrap_args",
                         view["agents"]["claude"]["experimental"])
        self.assertIn("agents.codex.raw_bwrap_args",
                      view["agents"]["codex"]["experimental"])

    def test_experimental_validate_warns_not_blocks(self):
        self.write_lince('version = "2.0"\n[experimental]\nraw_bwrap_args = ["--dev-bind", "/x", "/x"]\n')
        issues = []
        self.lc._validate_lince_file(self.lince_cfg, issues)
        self.assertTrue(any("policy-overridden" in i["message"] for i in issues))
        self.assertFalse(any(i["level"] == "error" for i in issues))

    def test_custom_agent_in_lince_toml(self):
        self.write_lince(
            'version = "2.0"\n'
            '[agents.bob]\n'
            'binary = "bob"\ndisplay_name = "Bob CLI"\nshort_label = "BOB"\n'
            'color = "magenta"\nprovider = "openai"\nlevel = "normal"\n'
            '[agents.bob.dashboard]\nhas_native_hooks = false\n'
            '[agents.bob.event_map]\nturn_end = "input"\n'
        )
        view = self.resolve()
        bob = view["agents"]["bob"]
        self.assertEqual(bob["display_name"], "Bob CLI")
        self.assertEqual(bob["event_map"], {"turn_end": "input"})
        self.assertEqual(bob["variants"]["unsandboxed"]["short_label"], "BOU")

    def test_malformed_lince_custom_agent_fails_that_agent_only(self):
        self.write_lince(
            'version = "2.0"\n'
            '[agents.broken]\ncolor = "red"\n'   # missing binary/display/label
            '[agents.claude]\nlevel = "paranoid"\n'
        )
        view = self.resolve()
        self.assertNotIn("broken", view["agents"])
        self.assertEqual(view["agents"]["claude"]["level"], "paranoid")
        self.assertTrue(any("broken" in w for w in view["warnings"]))

    # ── project overlay clamp (§2.4) ────────────────────────────────────

    def test_project_overlay_tighten_applies_loosen_clamped(self):
        self.write_lince('version = "2.0"\n[agents.claude]\nlevel = "normal"\n')
        project = Path(self.tmp.name) / "proj"
        (project / ".lince").mkdir(parents=True)
        (project / ".lince" / "lince.toml").write_text(
            '[agents.claude]\nlevel = "paranoid"\n'
            '[agents.codex]\nlevel = "permissive"\n'
            '[network]\nallowed_hosts = ["sketchy.example"]\n',
            encoding="utf-8",
        )
        view = self.resolve(project_dir=project)
        # tighten (normal → paranoid): applied silently
        self.assertEqual(view["agents"]["claude"]["level"], "paranoid")
        self.assertEqual(view["agents"]["claude"]["origin"]["level"], "project")
        # loosen (normal → permissive): ignored with a notice
        self.assertEqual(view["agents"]["codex"]["level"], "normal")
        self.assertNotIn("sketchy.example",
                         view["agents"]["claude"]["allowed_hosts_effective"])
        self.assertTrue(any("allow_loosening" in w for w in view["warnings"]))

    # ── misc contract ───────────────────────────────────────────────────

    def test_agent_filter(self):
        view = self.resolve(agent_filter="gemini")
        self.assertEqual(list(view["agents"]), ["gemini"])

    def test_cli_flags_override(self):
        view = self.resolve(flag_level="paranoid", flag_allow_hosts=["crates.io"])
        self.assertEqual(view["agents"]["claude"]["level"], "paranoid")
        self.assertEqual(view["agents"]["claude"]["origin"]["level"], "flag")
        self.assertIn("crates.io", view["agents"]["claude"]["allowed_hosts_effective"])

    def test_output_is_json_serializable_and_deterministic(self):
        a = json.dumps(self.resolve(), sort_keys=True)
        b = json.dumps(self.resolve(), sort_keys=True)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
