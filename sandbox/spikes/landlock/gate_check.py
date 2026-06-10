#!/usr/bin/env python3
"""In-sandbox assertions for the paranoid Landlock gate prototype (#211).

Executed by landlock_exec.py (already restricted) INSIDE the paranoid
bwrap sandbox, in place of a real agent binary. Proves the Landlock fence
holds in the exact runtime the agent would get:

  - bwrap mounts /tmp as a FRESH RW tmpfs at paranoid, so a denied write
    there can only be Landlock's doing (bwrap would have allowed it);
  - the denied TCP port has no listener in the fresh netns, so EACCES
    (instead of ECONNREFUSED) can only be Landlock's doing;
  - port 8118 is the in-sandbox socat bridge to the credential proxy —
    the one connect the paranoid policy allows.

Usage: gate_check.py <project_dir> (rw-allowed dir; everything else ro)
"""

import errno
import os
import socket
import subprocess
import sys

PROXY_PORT = 8118
DENIED_PORT = 9  # discard; nothing listens in the fresh netns

_results: list = []


def report(name: str, ok: bool, detail: str = "") -> None:
    _results.append(ok)
    suffix = f" — {detail}" if detail else ""
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{suffix}", flush=True)


def main(project_dir: str) -> int:
    print(f"gate_check: pid {os.getpid()} inside paranoid sandbox, "
          f"project {project_dir}", flush=True)

    # 1. write inside the project dir (rw rule) -> must succeed
    inside = os.path.join(project_dir, "inside.txt")
    try:
        with open(inside, "w") as f:
            f.write("ok\n")
        report("fs: write inside project dir succeeds", True, inside)
    except OSError as exc:
        report("fs: write inside project dir succeeds", False, str(exc))

    # 2. write to /tmp -> EACCES. bwrap mounted /tmp as a fresh RW tmpfs,
    # so this denial is provably Landlock's (EROFS would be bwrap's).
    denied_path = f"/tmp/landlock_denied_{os.getpid()}.txt"
    try:
        with open(denied_path, "w") as f:
            f.write("should not happen\n")
        report("fs: write to bwrap rw tmpfs /tmp denied by Landlock", False,
               f"{denied_path} was writable!")
    except OSError as exc:
        report("fs: write to bwrap rw tmpfs /tmp denied by Landlock",
               exc.errno == errno.EACCES,
               f"errno={errno.errorcode.get(exc.errno, exc.errno)}")

    # 3. read system files still works (ro rule on /)
    try:
        with open("/etc/os-release") as f:
            f.read()
        report("fs: read /etc (ro rule) still works", True)
    except OSError as exc:
        report("fs: read /etc (ro rule) still works", False, str(exc))

    # 4. connect to the socat proxy bridge on 8118 -> allowed
    try:
        with socket.create_connection(("127.0.0.1", PROXY_PORT), timeout=3):
            pass
        report(f"net: connect to proxy bridge port {PROXY_PORT} succeeds",
               True, "socat listener reached")
    except OSError as exc:
        report(f"net: connect to proxy bridge port {PROXY_PORT} succeeds",
               False, str(exc))

    # 5. connect to any other port -> EACCES (no listener in this netns,
    # so without Landlock this would be ECONNREFUSED)
    try:
        with socket.create_connection(("127.0.0.1", DENIED_PORT), timeout=3):
            pass
        report(f"net: connect to denied port {DENIED_PORT} blocked", False,
               "connect succeeded despite Landlock!")
    except OSError as exc:
        report(f"net: connect to denied port {DENIED_PORT} blocked",
               exc.errno == errno.EACCES,
               f"errno={errno.errorcode.get(exc.errno, exc.errno)} "
               f"(ECONNREFUSED would mean Landlock let it through)")

    # 6. bind -> EACCES (no bind rule in the paranoid gate)
    try:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.close()
        report("net: bind blocked (no bind rule)", False, "bind succeeded")
    except OSError as exc:
        report("net: bind blocked (no bind rule)",
               exc.errno == errno.EACCES,
               f"errno={errno.errorcode.get(exc.errno, exc.errno)}")

    # 7. inheritance: a fresh subprocess (fork+execve) is still confined
    grand = subprocess.run(
        [sys.executable, "-c", f"open({denied_path!r}, 'w').write('x')"],
        capture_output=True, text=True)
    report("inherit: subprocess still denied /tmp write",
           grand.returncode != 0 and "PermissionError" in grand.stderr,
           f"rc={grand.returncode}")

    print(flush=True)
    if all(_results):
        print("GATE RESULT: ALL CHECKS PASSED", flush=True)
        return 0
    print("GATE RESULT: FAILURES — see above", flush=True)
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: gate_check.py <project_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
