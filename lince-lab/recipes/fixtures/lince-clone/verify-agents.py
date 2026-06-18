#!/usr/bin/env python3
"""#202 contract check — the resolved agent list == enabled_agents, each once.

Runs the REAL ``lince-config resolve`` (installed in the guest from the staged
sources) and asserts the resolved view's agent list equals the expected
``enabled_agents`` passed as argv, each appearing exactly once. This is the #202
"agent list == enabled_agents, no per-sandbox-level duplication" contract,
checked against real code rather than a scripted grid.

Exit codes: 0 = contract holds; 1 = contract violated (wrong/duplicated list);
2 = resolve failed or produced non-JSON. Used by the lince-wizard recipe's
verify step (``python3 /work/verify-agents.py claude codex``).
"""

import json
import os
import subprocess
import sys


def main() -> int:
    expected = sorted(sys.argv[1:])
    # install.sh places the CLI at ~/.local/bin; make sure it is on PATH.
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + env.get("PATH", "")
    proc = subprocess.run(["lince-config", "resolve"], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        sys.stderr.write(f"lince-config resolve failed (exit {proc.returncode}): {proc.stderr.strip()}\n")
        return 2
    try:
        view = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"resolve output is not JSON: {exc}\n{proc.stdout[:500]}\n")
        return 2
    agents = sorted(view.get("agents", {}).keys())
    if agents != expected:
        sys.stderr.write(f"#202 contract violated: agent list {agents} != enabled_agents {expected}\n")
        return 1
    print(f"#202 OK: resolved agent list == enabled_agents == {agents} (each exactly once)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
