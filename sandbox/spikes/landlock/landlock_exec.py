#!/usr/bin/env python3
"""Landlock launcher shim — spike prototype of the future `agent-sandbox __landlock-exec` subcommand (#211).

Runs as the LAST element of the bwrap argv (Option B in
docs/design/landlock-spike.md Q2): it starts inside the final mount
namespace, opens its rule FDs there (so bwrap tmpfs and bind mounts are
exactly what the rules attach to), applies the ruleset, then execs the
real agent argv. Stdlib-only (ctypes), Python 3.11+.

Usage (everything before `--` is shim policy, everything after is the
agent command):

    landlock_exec.py [--rw DIR]... [--ro DIR]... \
                     [--connect-port N]... [--bind-port N]... \
                     [--fail-closed] -- ARGV...

Behaviour mirrors the recommendation in the design doc:
  - probe once; ABI 0 -> log and exec unrestricted (never fail), unless
    --fail-closed / LINCE_LANDLOCK_FAIL_CLOSED=1 (paranoid contract);
  - ABI 1-3 -> fs rules only, log that net is not enforced;
  - ABI >= 4 -> fs + TCP connect/bind port rules (deny-by-default).

Every run emits a single-line JSON **effective-policy record** to stderr
(prefix `LINCE_EFFECTIVE_POLICY: `; also written to the file named by
LINCE_POLICY_RECORD_PATH when set) stating what was *requested* vs what
the kernel actually *enforced* — see docs/design/landlock-spike.md
"Effective policy: requested vs enforced". LINCE_LANDLOCK_FORCE_ABI=N
caps the probed ABI to simulate older kernels (degraded-path demo).
"""

import argparse
import ctypes
import errno
import hashlib
import json
import os
import sys
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
                   connect_ports: list, bind_ports: list) -> float:
    """Self-restrict; returns setup time in microseconds."""
    t0 = time.perf_counter_ns()

    handled_fs = fs_rights_for_abi(abi)
    attr = RulesetAttr(handled_access_fs=handled_fs,
                       handled_access_net=0, scoped=0)
    size = 8                       # ABI 1-3: fs field only
    if abi >= 4:
        attr.handled_access_net = NET_BIND_TCP | NET_CONNECT_TCP
        size = 16

    ruleset_fd = _check(
        _libc.syscall(SYS_LANDLOCK_CREATE_RULESET, ctypes.byref(attr),
                      ctypes.c_size_t(size), ctypes.c_uint32(0)),
        "landlock_create_ruleset")
    try:
        for path, rights in ([(d, handled_fs) for d in rw_dirs]
                             + [(d, RO_EXEC) for d in ro_dirs]):
            if not os.path.isdir(path):
                continue
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
            for access, ports in ((NET_CONNECT_TCP, connect_ports),
                                  (NET_BIND_TCP, bind_ports)):
                for port in ports:
                    np = NetPortAttr(allowed_access=access, port=port)
                    _check(_libc.syscall(
                        SYS_LANDLOCK_ADD_RULE, ruleset_fd,
                        LANDLOCK_RULE_NET_PORT, ctypes.byref(np),
                        ctypes.c_uint32(0)),
                        f"landlock_add_rule(port {port})")
        _check(_libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0), "prctl(nnp)")
        _check(_libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd,
                             ctypes.c_uint32(0)),
               "landlock_restrict_self")
    finally:
        os.close(ruleset_fd)

    return (time.perf_counter_ns() - t0) / 1000.0


def _self_digest() -> str:
    """sha256 of this shim file — the record's helper_digest field."""
    with open(__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def emit_record(record: dict, record_file) -> None:
    """Single-line JSON to stderr (+ optional pre-opened record file)."""
    line = json.dumps(record, ensure_ascii=False)
    print(f"LINCE_EFFECTIVE_POLICY: {line}", file=sys.stderr, flush=True)
    if record_file is not None:
        record_file.write(line + "\n")
        record_file.close()


def main() -> int:
    argv = sys.argv[1:]
    if "--" not in argv:
        print("landlock_exec: usage: landlock_exec.py [--rw DIR]... "
              "[--ro DIR]... [--connect-port N]... [--bind-port N]... "
              "[--fail-closed] -- ARGV...", file=sys.stderr)
        return 2
    sep = argv.index("--")
    shim_argv, agent_argv = argv[:sep], argv[sep + 1:]
    if not agent_argv:
        print("landlock_exec: no agent command after '--'", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(prog="landlock_exec.py")
    parser.add_argument("--rw", action="append", default=[], metavar="DIR")
    parser.add_argument("--ro", action="append", default=[], metavar="DIR")
    parser.add_argument("--connect-port", action="append", type=int,
                        default=[], metavar="N")
    parser.add_argument("--bind-port", action="append", type=int,
                        default=[], metavar="N")
    parser.add_argument("--fail-closed", action="store_true")
    args = parser.parse_args(shim_argv)
    fail_closed = (args.fail_closed
                   or os.environ.get("LINCE_LANDLOCK_FAIL_CLOSED") == "1")

    # Defaults mirror the design doc Q4.4: ro+execute on the whole ro-bound
    # system view; rw must be explicit (project dir + binds).
    ro_dirs = args.ro if args.ro else ["/"]

    abi = probe_abi()
    forced = os.environ.get("LINCE_LANDLOCK_FORCE_ABI")
    if forced is not None:
        # Degraded-path demo: pretend the kernel is older than it is. Can
        # only lower the probed ABI, never raise it.
        abi = min(abi, int(forced))

    # Effective-policy record (rpelevin, #211): requested vs enforced.
    # Built BEFORE restriction (digest needs a file read; design doc Q4.3).
    record = {
        "backend": os.environ.get("LINCE_BACKEND", "bwrap"),
        "requested_level": os.environ.get("LINCE_SANDBOX_LEVEL"),
        "requested_fs": {"rw": args.rw, "ro": ro_dirs},
        "requested_net": {"connect_ports": args.connect_port,
                          "bind_ports": args.bind_port},
        "landlock_abi": abi,
        "fs_enforced": False,
        "net_enforced": False,
        # Landlock net rules (ABI >= 4) are TCP+port-based only — they can
        # never express host allowlists; that stays the proxy's job.
        "net_limitation": "unavailable",
        "applied_before_exec": False,
        # The shim cannot observe the agent after execvp; inheritance
        # across fork+execve is a kernel property, verified empirically by
        # demo.py / gate_check.py — stay honest about who verified what.
        "inherited_by_subprocesses": "by-design; verified by gate_check",
        "helper_digest": _self_digest(),
        # Only the launcher (agent-sandbox build_bwrap_cmd) knows the bwrap
        # argv; the in-sandbox shim never sees it. Production home for this
        # field is #221, where agent-sandbox assembles the full record.
        "bwrap_args_digest": None,
        "degraded_reason": None,
    }
    # Open the optional record file BEFORE restriction: its parent dir may
    # not be writable afterwards (the already-open fd still is).
    record_path = os.environ.get("LINCE_POLICY_RECORD_PATH")
    record_file = open(record_path, "w") if record_path else None

    if abi == 0:
        record["degraded_reason"] = ("landlock unavailable (ABI 0 — kernel "
                                     "without Landlock or LSM disabled)")
        emit_record(record, record_file)
        if fail_closed:
            print("landlock_exec: FAIL-CLOSED — requested filesystem and "
                  "network boundaries cannot be enforced (Landlock ABI 0); "
                  "refusing to exec the agent", file=sys.stderr)
            return 1
        print("landlock: not available — bwrap-only containment",
              file=sys.stderr)
        os.execvp(agent_argv[0], agent_argv)

    # Compute everything BEFORE restriction (design doc Q4.3): after
    # landlock_restrict_self() the shim itself is confined.
    setup_us = apply_landlock(abi, rw_dirs=args.rw, ro_dirs=ro_dirs,
                              connect_ports=args.connect_port,
                              bind_ports=args.bind_port)

    record["fs_enforced"] = True
    record["applied_before_exec"] = True
    net_requested = bool(args.connect_port or args.bind_port)
    if abi >= 4:
        record["net_enforced"] = True
        record["net_limitation"] = "port-only, host-unaware"
    elif net_requested:
        record["degraded_reason"] = (f"network rules not enforced "
                                     f"(ABI {abi} < 4)")
    emit_record(record, record_file)

    if fail_closed and net_requested and not record["net_enforced"]:
        print(f"landlock_exec: FAIL-CLOSED — requested network boundary "
              f"cannot be enforced (ABI {abi} < 4); refusing to exec the "
              f"agent", file=sys.stderr)
        return 1

    enforced = "fs+net" if abi >= 4 else "fs only"
    if abi < 4 and net_requested:
        print(f"landlock: network rules not enforced (ABI {abi} < 4)",
              file=sys.stderr)
    print(f"landlock: {enforced} (ABI {abi}) applied in {setup_us:.1f} us — "
          f"rw={args.rw} connect={args.connect_port} bind={args.bind_port}",
          file=sys.stderr)
    os.execvp(agent_argv[0], agent_argv)
    return 1  # unreachable


if __name__ == "__main__":
    sys.exit(main())
