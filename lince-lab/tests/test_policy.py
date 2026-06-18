#!/usr/bin/env python3
"""Policy gate tests (blueprint §3) — pure, exhaustive, no VM.

:func:`lince_lab.policy.check` is a pure function, so every section-3 rule is
asserted directly here with crafted args and a fake ``home``:

* §3.1 server-side template forcing — a client ``template_yaml`` is dropped;
* §3.2 network deny-by-default — ``allow`` without an allowlist is denied;
* §3.3 copy_in path bounding — ``..`` / absolute-outside / secret dirs are denied;
* §3.4 credential stripping — ``*_TOKEN`` / ``*_KEY`` / known names removed;
* §3.5 name-prefix guard — a non-``lince-lab-`` VM name is denied.

Run with:
    python3 lince-lab/tests/test_policy.py
"""

import pathlib
import sys
import tempfile
import unittest

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab.errors import POLICY_DENIED, PolicyDenied  # noqa: E402
from lince_lab.policy import (  # noqa: E402
    VM_NAME_PREFIX,
    artifacts_root,
    check,
    check_capture,
    is_secret_env_key,
    strip_secret_env,
)

LAB_VM = "lince-lab-demo"


class NamePrefixTests(unittest.TestCase):
    """§3.5 — only ``lince-lab-`` prefixed VMs may be operated on."""

    def test_prefixed_name_passes(self):
        out = check("vm.start", {"name": LAB_VM})
        self.assertEqual(out["name"], LAB_VM)

    def test_unprefixed_name_denied(self):
        with self.assertRaises(PolicyDenied) as ctx:
            check("vm.start", {"name": "my-personal-vm"})
        self.assertEqual(ctx.exception.exit_code, POLICY_DENIED)

    def test_missing_name_denied(self):
        with self.assertRaises(PolicyDenied):
            check("vm.exec", {"argv": ["true"]})

    def test_prefix_constant_is_enforced(self):
        # A name that merely contains the prefix mid-string is still denied.
        with self.assertRaises(PolicyDenied):
            check("vm.delete", {"name": f"x-{VM_NAME_PREFIX}demo"})

    def test_non_named_verbs_skip_prefix_guard(self):
        # ping carries no VM name and must not trip the guard.
        out = check("ping", {})
        self.assertEqual(out, {})


class TemplateForcingTests(unittest.TestCase):
    """§3.1 — a client-supplied vm.create template is never trusted."""

    def test_client_template_is_stripped(self):
        out = check("vm.create", {"name": LAB_VM, "template_yaml": "mounts: [/home]"})
        self.assertNotIn("template_yaml", out)

    def test_create_without_template_unchanged(self):
        out = check("vm.create", {"name": LAB_VM})
        self.assertNotIn("template_yaml", out)
        self.assertEqual(out["name"], LAB_VM)

    def test_input_args_not_mutated(self):
        original = {"name": LAB_VM, "template_yaml": "evil"}
        check("vm.create", original)
        # The caller's dict is untouched; only the returned copy is rewritten.
        self.assertIn("template_yaml", original)


class NetworkAllowlistTests(unittest.TestCase):
    """§3.2 — deny is default; allow requires a non-empty allowlist."""

    def test_deny_mode_passes(self):
        ctx = {"network": {"mode": "deny"}}
        out = check("recipe.run", {"recipe": "r.toml"}, ctx)
        self.assertEqual(out["recipe"], "r.toml")

    def test_missing_network_defaults_to_deny(self):
        out = check("recipe.run", {"recipe": "r.toml"}, {})
        self.assertEqual(out["recipe"], "r.toml")

    def test_allow_without_allowlist_denied(self):
        ctx = {"network": {"mode": "allow", "allow_hosts": [], "allow_ports": []}}
        with self.assertRaises(PolicyDenied) as exc:
            check("recipe.run", {"recipe": "r.toml"}, ctx)
        self.assertEqual(exc.exception.exit_code, POLICY_DENIED)

    def test_allow_with_hosts_passes(self):
        ctx = {"network": {"mode": "allow", "allow_hosts": ["registry.npmjs.org"]}}
        out = check("bisect.run", {"recipe": "r.toml"}, ctx)
        self.assertEqual(out["recipe"], "r.toml")

    def test_allow_with_ports_passes(self):
        ctx = {"network": {"mode": "allow", "allow_ports": [443]}}
        out = check("recipe.run", {"recipe": "r.toml"}, ctx)
        self.assertEqual(out["recipe"], "r.toml")


class CopyInBoundsTests(unittest.TestCase):
    """§3.3 — copy_in host paths must resolve under the recipe workspace."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name) / "home"
        self.workspace = self.home / "proj" / "fixtures"
        self.workspace.mkdir(parents=True)
        (self.workspace / "stage").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _ctx(self):
        return {"workspace_dir": str(self.workspace)}

    def test_path_under_workspace_passes(self):
        out = check(
            "vm.copy_in",
            {"name": LAB_VM, "host_path": str(self.workspace / "stage"), "guest_path": "/work"},
            self._ctx(),
            home=self.home,
        )
        self.assertEqual(out["guest_path"], "/work")

    def test_relative_dotdot_escape_denied(self):
        with self.assertRaises(PolicyDenied) as exc:
            check(
                "vm.copy_in",
                {"name": LAB_VM, "host_path": "../../etc", "guest_path": "/work"},
                self._ctx(),
                home=self.home,
            )
        self.assertEqual(exc.exception.exit_code, POLICY_DENIED)

    def test_absolute_outside_denied(self):
        with self.assertRaises(PolicyDenied):
            check(
                "vm.copy_in",
                {"name": LAB_VM, "host_path": "/etc/passwd", "guest_path": "/work"},
                self._ctx(),
                home=self.home,
            )

    def test_secret_ssh_dir_denied(self):
        ssh = self.home / ".ssh"
        ssh.mkdir(parents=True)
        with self.assertRaises(PolicyDenied):
            check(
                "vm.copy_in",
                {"name": LAB_VM, "host_path": str(ssh / "id_rsa"), "guest_path": "/work"},
                {"workspace_dir": str(self.home)},
                home=self.home,
            )

    def test_secret_config_lince_denied(self):
        cfg = self.home / ".config" / "lince"
        cfg.mkdir(parents=True)
        with self.assertRaises(PolicyDenied):
            check(
                "vm.copy_in",
                {"name": LAB_VM, "host_path": str(cfg), "guest_path": "/work"},
                {"workspace_dir": str(self.home)},
                home=self.home,
            )

    def test_missing_workspace_context_denied(self):
        with self.assertRaises(PolicyDenied):
            check(
                "vm.copy_in",
                {"name": LAB_VM, "host_path": str(self.workspace), "guest_path": "/work"},
                {},
                home=self.home,
            )

    def test_missing_host_path_denied(self):
        with self.assertRaises(PolicyDenied):
            check("vm.copy_in", {"name": LAB_VM, "guest_path": "/work"}, self._ctx(), home=self.home)

    def test_forged_root_workspace_denied(self):
        # A client-forged workspace_dir of the filesystem root must NOT let an
        # in-"workspace" /etc/shadow exfiltrate: the workspace itself is rejected.
        with self.assertRaises(PolicyDenied) as exc:
            check(
                "vm.copy_in",
                {"name": LAB_VM, "host_path": "/etc/shadow", "guest_path": "/work"},
                {"workspace_dir": "/"},
                home=self.home,
            )
        self.assertEqual(exc.exception.exit_code, POLICY_DENIED)

    def test_forged_home_workspace_denied(self):
        # The bare home spans every secret dir, so it is too broad to be trusted.
        with self.assertRaises(PolicyDenied):
            check(
                "vm.copy_in",
                {"name": LAB_VM, "host_path": str(self.home / "anything"), "guest_path": "/work"},
                {"workspace_dir": str(self.home)},
                home=self.home,
            )


class CopyOutBoundsTests(unittest.TestCase):
    """§3.4 — copy_out host destinations must resolve under the artifacts root."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name) / "home"
        self.home.mkdir(parents=True)
        self.artifacts = artifacts_root(self.home)
        self.artifacts.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_in_bounds_destination_allowed(self):
        out = check(
            "vm.copy_out",
            {"name": LAB_VM, "guest_path": "/work/out.log", "host_path": str(self.artifacts / "out.log")},
            home=self.home,
        )
        self.assertEqual(out["guest_path"], "/work/out.log")

    def test_absolute_outside_destination_denied(self):
        with self.assertRaises(PolicyDenied) as exc:
            check(
                "vm.copy_out",
                {"name": LAB_VM, "guest_path": "/etc/passwd", "host_path": "/etc/cron.d/evil"},
                home=self.home,
            )
        self.assertEqual(exc.exception.exit_code, POLICY_DENIED)

    def test_dotdot_escape_destination_denied(self):
        with self.assertRaises(PolicyDenied):
            check(
                "vm.copy_out",
                {"name": LAB_VM, "guest_path": "/work/x", "host_path": str(self.artifacts / ".." / ".." / "evil")},
                home=self.home,
            )

    def test_secret_destination_denied(self):
        ssh = self.home / ".ssh"
        ssh.mkdir(parents=True)
        with self.assertRaises(PolicyDenied):
            check(
                "vm.copy_out",
                {"name": LAB_VM, "guest_path": "/work/key", "host_path": str(ssh / "authorized_keys")},
                home=self.home,
            )

    def test_missing_host_path_denied(self):
        with self.assertRaises(PolicyDenied):
            check("vm.copy_out", {"name": LAB_VM, "guest_path": "/work/x"}, home=self.home)


class CaptureGateTests(unittest.TestCase):
    """§3 — capture-stream verbs are policy-checked, not a bypass."""

    def test_capture_send_is_checked(self):
        out = check_capture("capture.send", {"payload": "ls\n"})
        self.assertEqual(out["payload"], "ls\n")

    def test_capture_snapshot_is_checked(self):
        out = check_capture("capture.snapshot", {"timeout_s": 5})
        self.assertEqual(out["timeout_s"], 5)

    def test_non_capture_verb_on_stream_denied(self):
        with self.assertRaises(PolicyDenied) as exc:
            check_capture("vm.exec", {"name": LAB_VM, "argv": ["true"]})
        self.assertEqual(exc.exception.exit_code, POLICY_DENIED)


class SecretHostPathTests(unittest.TestCase):
    """§3.3 — the expanded secret-location denylist + sibling-escape safety."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name) / "home"
        # A broad workspace = home, so the only thing under test is the secret
        # denylist (the home-too-broad guard fires first, which is also a denial —
        # so here we use a workspace that contains the secret to isolate intent).
        self.workspace = self.home
        self.home.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _copy_in(self, host_path: str, workspace: str | None = None):
        return check(
            "vm.copy_in",
            {"name": LAB_VM, "host_path": host_path, "guest_path": "/work"},
            {"workspace_dir": workspace or str(self.workspace / "proj")},
            home=self.home,
        )

    def test_new_secret_dirs_denied(self):
        proj = self.home / "proj"
        proj.mkdir()
        # Symlink-free direct secret paths under home; workspace=proj is narrow.
        for rel in (".netrc", ".git-credentials", ".kube/config", ".docker/config.json"):
            target = self.home / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with self.assertRaises(PolicyDenied, msg=rel):
                self._copy_in(str(target))

    def test_etc_ssh_denied(self):
        with self.assertRaises(PolicyDenied):
            self._copy_in("/etc/ssh/sshd_config")

    def test_sibling_of_secret_dir_not_a_false_secret(self):
        # ~/.ssh-backup is a SIBLING, not under ~/.ssh: it must not match the
        # ~/.ssh rule by string prefix. It is still denied here only because it is
        # outside the narrow workspace — i.e. the secret check does NOT fire.
        from lince_lab.policy import _is_secret_host_path  # noqa: PLC0415

        sibling = self.home / ".ssh-backup" / "id_rsa"
        self.assertFalse(_is_secret_host_path(str(sibling), self.home))
        # And under its own workspace it copies in fine (proves it is not a secret).
        ws = self.home / ".ssh-backup"
        ws.mkdir(parents=True)
        out = self._copy_in(str(ws / "data"), workspace=str(ws))
        self.assertEqual(out["guest_path"], "/work")


class SecretEnvTests(unittest.TestCase):
    """§3.4 — credential env keys are stripped before exec is forwarded."""

    def test_token_suffix_detected(self):
        self.assertTrue(is_secret_env_key("MY_TOKEN"))
        self.assertTrue(is_secret_env_key("anything_key"))  # case-insensitive
        self.assertTrue(is_secret_env_key("DB_PASSWORD"))

    def test_known_name_detected(self):
        self.assertTrue(is_secret_env_key("AWS_SECRET_ACCESS_KEY"))
        self.assertTrue(is_secret_env_key("GITHUB_TOKEN"))

    def test_expanded_denylist_detected(self):
        # New exact names and patterns must be stripped (blueprint §3.5).
        for key in ("KUBECONFIG", "DATABASE_URL", "AWS_PROFILE", "SSH_AUTH_SOCK"):
            self.assertTrue(is_secret_env_key(key), key)
        self.assertTrue(is_secret_env_key("SENTRY_DSN"))  # *_DSN suffix
        self.assertTrue(is_secret_env_key("CLOUDSDK_CONFIG"))  # CLOUDSDK_ prefix
        self.assertTrue(is_secret_env_key("cloudsdk_core_project"))  # case-insensitive

    def test_plain_key_kept(self):
        self.assertFalse(is_secret_env_key("PATH"))
        self.assertFalse(is_secret_env_key("LANG"))
        self.assertFalse(is_secret_env_key("KUBE_PROMPT"))  # not the KUBECONFIG name

    def test_strip_removes_only_secrets(self):
        env = {"PATH": "/usr/bin", "GH_TOKEN": "x", "API_KEY": "y", "HOME": "/h"}
        cleaned = strip_secret_env(env)
        self.assertEqual(cleaned, {"PATH": "/usr/bin", "HOME": "/h"})

    def test_check_strips_exec_env(self):
        out = check(
            "vm.exec",
            {"name": LAB_VM, "argv": ["env"], "env": {"PATH": "/bin", "SECRET_KEY": "s"}},
        )
        self.assertEqual(out["env"], {"PATH": "/bin"})

    def test_check_exec_without_env_is_fine(self):
        out = check("vm.exec", {"name": LAB_VM, "argv": ["true"]})
        self.assertEqual(out["argv"], ["true"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
