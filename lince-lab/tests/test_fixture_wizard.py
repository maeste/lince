#!/usr/bin/env python3
"""#259 substrate-free proof — verify-agents.py is the #202 oracle, no VM.

The lince-wizard recipe (Option A) installs the real lince-config in a guest,
seeds ``enabled_agents``, and runs ``verify-agents.py`` which asserts
``lince-config resolve``'s agent list == enabled_agents, each once (the #202
"no per-sandbox-level duplication" contract). The deep resolve logic is owned by
lince-config's own tests; here we prove the *recipe's verdict script* catches the
contract without a VM, by running it against a FAKE ``lince-config`` that emits a
GOOD vs a contract-VIOLATING resolved view. We also assert the shipped recipe
wires that script into an exit_code-gated step.

Run with:
    python3 lince-lab/tests/test_fixture_wizard.py
"""

import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

# Put the package dir (lince-lab/) on sys.path so absolute imports resolve.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lince_lab.recipe import load_recipe  # noqa: E402

_FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / "recipes" / "fixtures" / "lince-clone"
VERIFY_SCRIPT = _FIXTURE_DIR / "verify-agents.py"
WIZARD_RECIPE = pathlib.Path(__file__).resolve().parent.parent / "recipes" / "lince-wizard.toml"


def _run_verify_against(resolve_json: str | None, *expected_agents: str) -> int:
    """Run verify-agents.py with a fake `lince-config` emitting ``resolve_json``.

    A throwaway HOME holds a fake ``~/.local/bin/lince-config`` (the path
    verify-agents.py puts first on PATH). ``resolve_json=None`` makes the fake
    exit nonzero (models a resolve failure). Returns verify-agents.py's exit code.
    """
    with tempfile.TemporaryDirectory() as home:
        bindir = pathlib.Path(home) / ".local" / "bin"
        bindir.mkdir(parents=True)
        fake = bindir / "lince-config"
        if resolve_json is None:
            fake.write_text("#!/bin/sh\necho 'boom' >&2\nexit 3\n", encoding="utf-8")
        else:
            # Emit the canned resolve JSON only for `resolve`; ignore other argv.
            fake.write_text(
                "#!/bin/sh\n"
                'if [ "$1" = "resolve" ]; then\n'
                f"cat <<'JSON'\n{resolve_json}\nJSON\n"
                "else\n  exit 0\nfi\n",
                encoding="utf-8",
            )
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        env = dict(os.environ)
        env["HOME"] = home
        proc = subprocess.run(
            [sys.executable, str(VERIFY_SCRIPT), *expected_agents],
            capture_output=True,
            text=True,
            env=env,
        )
        return proc.returncode


GOOD = '{"agents": {"claude": {}, "codex": {}}}'
EXTRA = '{"agents": {"claude": {}, "codex": {}, "gemini": {}}}'
MISSING = '{"agents": {"claude": {}}}'


class VerifyAgentsTest(unittest.TestCase):
    def test_good_resolve_matches_enabled_agents(self) -> None:
        self.assertEqual(_run_verify_against(GOOD, "claude", "codex"), 0)

    def test_extra_agent_violates_contract(self) -> None:
        # An agent beyond enabled_agents (e.g. a #202-style leak) → exit 1.
        self.assertEqual(_run_verify_against(EXTRA, "claude", "codex"), 1)

    def test_missing_agent_violates_contract(self) -> None:
        self.assertEqual(_run_verify_against(MISSING, "claude", "codex"), 1)

    def test_resolve_failure_is_exit_2(self) -> None:
        self.assertEqual(_run_verify_against(None, "claude", "codex"), 2)

    def test_non_json_resolve_is_exit_2(self) -> None:
        self.assertEqual(_run_verify_against("not json at all", "claude", "codex"), 2)


class WizardRecipeWiringTest(unittest.TestCase):
    """The shipped recipe must wire verify-agents.py into an exit_code-gated step."""

    def test_recipe_runs_verify_script_and_asserts_exit_code(self) -> None:
        recipe = load_recipe(WIZARD_RECIPE)
        runs = [step.get("run", []) for step in recipe.steps]
        self.assertIn(["python3", "/work/verify-agents.py", "claude", "codex"], runs)
        # The verdict is gated: the recipe asserts every step exits 0.
        self.assertEqual(recipe.assertions.get("exit_code"), 0)
        # Deny network — the wizard check is fully local.
        self.assertEqual(recipe.network.get("mode"), "deny")


if __name__ == "__main__":
    unittest.main(verbosity=2)
