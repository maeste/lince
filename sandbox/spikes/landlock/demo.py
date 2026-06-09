#!/usr/bin/env python3
"""Landlock self-restriction demo — stdlib-only (ctypes), no external deps.

Demonstrates the exact pattern agent-sandbox would use as a
defense-in-depth layer inside the bwrap backend (#211):

  parent (host side)
    - creates a temp "project dir" and two local TCP listeners
      (one allowed port, one denied port — both REAL listeners so a
      blocked connect is provably Landlock, not ECONNREFUSED)
    - spawns a child process (stand-in for the launcher between bwrap
      setup and agent exec)

  child (sandbox side)
    - probes the Landlock ABI (graceful degradation on ENOSYS et al.)
    - builds a ruleset: full rw beneath the project dir, ro+execute on
      system paths (/usr, /etc, ...), TCP connect allowed ONLY to the
      allowed port (ABI >= 4)
    - landlock_restrict_self() — measured with perf_counter_ns
    - proves: write inside allowed dir OK, write outside EACCES,
      connect allowed port OK, connect denied port EACCES
    - INHERITANCE: subprocess.run() a fresh python3 after restriction —
      the grandchild is still confined (Landlock rulesets are inherited
      across fork+execve, like no_new_privs)

Run:  python3 sandbox/spikes/landlock/demo.py
Exit: 0 all checks pass (or Landlock unavailable -> graceful skip),
      1 a check failed.
"""

import ctypes
import errno
import os
import socket
import subprocess
import sys
import tempfile
import time

# --- Landlock UAPI (include/uapi/linux/landlock.h) -------------------------

SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446

LANDLOCK_CREATE_RULESET_VERSION = 1 << 0

LANDLOCK_RULE_PATH_BENEATH = 1
LANDLOCK_RULE_NET_PORT = 2

# Filesystem access rights (bit -> minimum ABI)
FS_RIGHTS = {
    "EXECUTE":     (1 << 0, 1),
    "WRITE_FILE":  (1 << 1, 1),
    "READ_FILE":   (1 << 2, 1),
    "READ_DIR":    (1 << 3, 1),
    "REMOVE_DIR":  (1 << 4, 1),
    "REMOVE_FILE": (1 << 5, 1),
    "MAKE_CHAR":   (1 << 6, 1),
    "MAKE_DIR":    (1 << 7, 1),
    "MAKE_REG":    (1 << 8, 1),
    "MAKE_SOCK":   (1 << 9, 1),
    "MAKE_FIFO":   (1 << 10, 1),
    "MAKE_BLOCK":  (1 << 11, 1),
    "MAKE_SYM":    (1 << 12, 1),
    "REFER":       (1 << 13, 2),
    "TRUNCATE":    (1 << 14, 3),
    "IOCTL_DEV":   (1 << 15, 5),
}

NET_BIND_TCP = 1 << 0     # ABI >= 4
NET_CONNECT_TCP = 1 << 1  # ABI >= 4

PR_SET_NO_NEW_PRIVS = 38

_libc = ctypes.CDLL(None, use_errno=True)


def _check(res: int, what: str) -> int:
    if res < 0:
        err = ctypes.get_errno()
        raise OSError(err, f"{what}: {os.strerror(err)}")
    return res


class RulesetAttr(ctypes.Structure):
    # struct landlock_ruleset_attr (ABI >= 6 layout; kernel accepts any
    # prefix size, we send only the fields the probed ABI knows about).
    _fields_ = [
        ("handled_access_fs", ctypes.c_uint64),
        ("handled_access_net", ctypes.c_uint64),  # ABI >= 4
        ("scoped", ctypes.c_uint64),              # ABI >= 6
    ]


class PathBeneathAttr(ctypes.Structure):
    _pack_ = 1  # __attribute__((packed)) in the UAPI header
    _layout_ = "ms"  # silence 3.14 DeprecationWarning; ignored pre-3.13
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


class NetPortAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("port", ctypes.c_uint64),
    ]


def probe_abi() -> int:
    """Landlock ABI version, 0 if unavailable (graceful degradation)."""
    res = _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, None,
                        ctypes.c_size_t(0),
                        ctypes.c_uint32(LANDLOCK_CREATE_RULESET_VERSION))
    if res < 0:
        err = ctypes.get_errno()
        if err in (errno.ENOSYS, errno.EOPNOTSUPP):
            return 0
        raise OSError(err, os.strerror(err))
    return res


def fs_rights_for_abi(abi: int) -> int:
    return sum(bit for bit, min_abi in FS_RIGHTS.values() if abi >= min_abi)


RO_EXEC = (FS_RIGHTS["EXECUTE"][0] | FS_RIGHTS["READ_FILE"][0]
           | FS_RIGHTS["READ_DIR"][0])


def apply_landlock(abi: int, rw_dirs: list, ro_dirs: list,
                   allowed_connect_ports: list) -> float:
    """Self-restrict; returns setup time in microseconds."""
    t0 = time.perf_counter_ns()

    handled_fs = fs_rights_for_abi(abi)
    attr = RulesetAttr(handled_access_fs=handled_fs,
                       handled_access_net=0, scoped=0)
    size = 8                       # ABI 1-3: fs field only
    if abi >= 4:
        attr.handled_access_net = NET_BIND_TCP | NET_CONNECT_TCP
        size = 16
    # NOTE: we deliberately do NOT handle `scoped` (ABI 6 IPC scoping)
    # in this demo — agent subprocesses must signal each other.

    ruleset_fd = _check(
        _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, ctypes.byref(attr),
                      ctypes.c_size_t(size), ctypes.c_uint32(0)),
        "landlock_create_ruleset")
    try:
        for path, rights in ([(d, handled_fs) for d in rw_dirs]
                             + [(d, RO_EXEC) for d in ro_dirs]):
            if not os.path.isdir(path):
                continue
            # O_PATH dir FD — Landlock rules reference *opened* FDs, so
            # what matters is the file the path resolves to NOW (in the
            # current mount namespace), not the string.
            dir_fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                pb = PathBeneathAttr(
                    allowed_access=rights & handled_fs, parent_fd=dir_fd)
                _check(_libc.syscall(
                    SYS_LANDLOCK_ADD_RULE, ruleset_fd,
                    LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(pb),
                    ctypes.c_uint32(0)), f"landlock_add_rule({path})")
            finally:
                os.close(dir_fd)
        if abi >= 4:
            for port in allowed_connect_ports:
                np = NetPortAttr(allowed_access=NET_CONNECT_TCP, port=port)
                _check(_libc.syscall(
                    SYS_LANDLOCK_ADD_RULE, ruleset_fd,
                    LANDLOCK_RULE_NET_PORT, ctypes.byref(np),
                    ctypes.c_uint32(0)), f"landlock_add_rule(port {port})")
        _check(_libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0), "prctl(nnp)")
        _check(_libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd,
                             ctypes.c_uint32(0)),
               "landlock_restrict_self")
    finally:
        os.close(ruleset_fd)

    return (time.perf_counter_ns() - t0) / 1000.0


# --- test harness -----------------------------------------------------------

PASS, FAIL = "PASS", "FAIL"
_results: list = []


def report(name: str, ok: bool, detail: str = "") -> None:
    _results.append(ok)
    suffix = f" — {detail}" if detail else ""
    print(f"  [{PASS if ok else FAIL}] {name}{suffix}")


def child_main(project_dir: str, allowed_port: int, denied_port: int) -> int:
    abi = probe_abi()
    if abi == 0:
        # Graceful degradation: exactly what agent-sandbox would do.
        print("Landlock unavailable on this kernel (ENOSYS/EOPNOTSUPP).")
        print("agent-sandbox would log a warning and continue with "
              "bwrap-only containment. Skipping demo (not a failure).")
        return 0
    print(f"child: Landlock ABI {abi}, restricting self...")

    ro_dirs = ["/usr", "/etc", "/lib", "/lib64", "/bin", "/sbin",
               "/proc", "/dev"]
    setup_us = apply_landlock(
        abi, rw_dirs=[project_dir], ro_dirs=ro_dirs,
        allowed_connect_ports=[allowed_port])
    print(f"child: ruleset built + applied in {setup_us:.1f} us "
          f"({len(ro_dirs) + 1} path rules, "
          f"{1 if abi >= 4 else 0} net rules)")

    # 1. write INSIDE the allowed project dir -> must succeed
    try:
        inside = os.path.join(project_dir, "inside.txt")
        with open(inside, "w") as f:
            f.write("ok\n")
        report("fs: write inside allowed dir succeeds", True, inside)
    except OSError as exc:
        report("fs: write inside allowed dir succeeds", False, str(exc))

    # 2. write OUTSIDE (parent of the project dir) -> EACCES.
    # NB: do not call tempfile.gettempdir() after restriction — it probes
    # for a writable dir and finds none (which itself proves the lockdown).
    outside = os.path.join(os.path.dirname(project_dir),
                           f"landlock_denied_{os.getpid()}.txt")
    try:
        with open(outside, "w") as f:
            f.write("should not happen\n")
        report("fs: write outside allowed dir denied", False,
               f"{outside} was writable!")
        os.unlink(outside)
    except OSError as exc:
        report("fs: write outside allowed dir denied",
               exc.errno == errno.EACCES,
               f"errno={errno.errorcode.get(exc.errno, exc.errno)}")

    # 3. read of system files still works (ro rule)
    try:
        with open("/etc/hostname") as f:
            f.read()
        report("fs: read /etc (ro rule) still works", True)
    except OSError as exc:
        report("fs: read /etc (ro rule) still works", False, str(exc))

    # 4. network (ABI >= 4): port-based TCP connect rules
    if abi >= 4:
        try:
            with socket.create_connection(("127.0.0.1", allowed_port),
                                          timeout=3):
                pass
            report(f"net: connect to allowed port {allowed_port} succeeds",
                   True)
        except OSError as exc:
            report(f"net: connect to allowed port {allowed_port} succeeds",
                   False, str(exc))
        try:
            with socket.create_connection(("127.0.0.1", denied_port),
                                          timeout=3):
                pass
            report(f"net: connect to denied port {denied_port} blocked",
                   False, "connect succeeded despite Landlock!")
        except OSError as exc:
            report(f"net: connect to denied port {denied_port} blocked",
                   exc.errno == errno.EACCES,
                   f"errno={errno.errorcode.get(exc.errno, exc.errno)} "
                   f"(listener IS running — denial is Landlock's)")
        try:
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            s.close()
            report("net: bind blocked (no bind rule added)", False,
                   "bind succeeded")
        except OSError as exc:
            report("net: bind blocked (no bind rule added)",
                   exc.errno == errno.EACCES,
                   f"errno={errno.errorcode.get(exc.errno, exc.errno)}")
    else:
        print(f"  [SKIP] net rules: ABI {abi} < 4 — agent-sandbox would "
              f"enforce fs only and log this")

    # 5. INHERITANCE: restriction survives fork + execve of a subprocess
    grand = subprocess.run(
        [sys.executable, "-c",
         f"open({outside!r}, 'w').write('x')"],
        capture_output=True, text=True)
    report("inherit: subprocess (fork+execve) still denied outside write",
           grand.returncode != 0 and "PermissionError" in grand.stderr,
           f"rc={grand.returncode}")
    grand_ok = subprocess.run(
        [sys.executable, "-c",
         f"open({os.path.join(project_dir, 'sub.txt')!r}, 'w').write('x')"],
        capture_output=True, text=True)
    report("inherit: subprocess can still write inside allowed dir",
           grand_ok.returncode == 0,
           f"rc={grand_ok.returncode} {grand_ok.stderr.strip()}")

    return 0 if all(_results) else 1


def parent_main() -> int:
    print(f"Landlock demo — kernel {os.uname().release}")
    abi = probe_abi()
    if abi == 0:
        print("Landlock unavailable (ENOSYS/EOPNOTSUPP) — graceful skip.")
        return 0

    with tempfile.TemporaryDirectory(prefix="landlock_demo_") as project:
        # Two REAL listeners: blocked connect must be EACCES, never
        # ECONNREFUSED, to prove it is Landlock doing the blocking.
        allowed_srv = socket.socket()
        allowed_srv.bind(("127.0.0.1", 0))
        allowed_srv.listen(8)
        denied_srv = socket.socket()
        denied_srv.bind(("127.0.0.1", 0))
        denied_srv.listen(8)
        allowed_port = allowed_srv.getsockname()[1]
        denied_port = denied_srv.getsockname()[1]
        print(f"parent: project dir {project}")
        print(f"parent: allowed port {allowed_port}, "
              f"denied port {denied_port} (both have live listeners)")

        child = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--child",
             project, str(allowed_port), str(denied_port)])
        allowed_srv.close()
        denied_srv.close()

        print()
        if child.returncode == 0:
            print("RESULT: ALL CHECKS PASSED")
        else:
            print("RESULT: FAILURES — see above")
        return child.returncode


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--child":
        sys.exit(child_main(sys.argv[2], int(sys.argv[3]),
                            int(sys.argv[4])))
    sys.exit(parent_main())
