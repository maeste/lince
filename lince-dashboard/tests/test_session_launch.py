"""#390 client mobility: the launcher targets a named Zellij session."""
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
launcher = runpy.run_path(str(ROOT / "lince-dashboard-launch"))


class SessionLaunchTests(unittest.TestCase):
    def test_attach_when_exact_session_exists_live_or_exited(self):
        resolve = launcher["resolve_session_action"]
        listing = "lince [Created 2h 3m ago]\nscratch [Created 5s ago]\n"
        self.assertEqual(resolve("lince", listing), "attach")
        exited = "lince [EXITED 2026-09-29 10:00:00]\n"
        self.assertEqual(resolve("lince", exited), "attach",
                         "exited sessions attach too (zellij resurrection)")

    def test_create_when_session_missing_or_only_prefix_match(self):
        resolve = launcher["resolve_session_action"]
        self.assertEqual(resolve("lince", ""), "create")
        # No prefix collisions: "lince" must not attach to "lince-test".
        self.assertEqual(resolve("lince", "lince-test [Created 1m ago]\n"), "create")
        self.assertEqual(resolve("lince-test", "lince [Created 1m ago]\n"), "create")

    def test_session_management_defaults_and_config_kdl_contract(self):
        # on_force_close must be explicit detach: the session outlives the client.
        config = (ROOT / "zellij-config/config.kdl").read_text()
        self.assertIn('on_force_close "detach"', config)
        self.assertNotIn('on_force_close "quit"', config)
        # Alt+o opens the interactive pane into the selected agent's host (#391).
        self.assertIn('bind "Alt o" { MessagePlugin { name "lince-open-remote"; }; }', config)
        self.assertIn('bind "Ctrl o" { MessagePlugin { name "lince-open-remote"; }; }', config)


if __name__ == "__main__":
    unittest.main()
