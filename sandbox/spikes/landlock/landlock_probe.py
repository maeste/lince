#!/usr/bin/env python3
"""Landlock ABI probe — stdlib-only (ctypes), no external deps.

Queries the kernel for the supported Landlock ABI version via

    landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION)

and prints the feature set that ABI level implies. Exit codes:

    0  Landlock available (ABI printed)
    1  Landlock not available (ENOSYS / EOPNOTSUPP / disabled LSM)
    2  unexpected error

This is the exact probe agent-sandbox would run at startup to decide
what to enforce (graceful degradation: enforce only what the running
kernel supports, log the rest as "not enforced").

Spike: https://github.com/RisorseArtificiali/lince/issues/211
"""

import ctypes
import errno
import os
import sys

# x86_64 / aarch64 / riscv64 share these syscall numbers (asm-generic).
SYS_LANDLOCK_CREATE_RULESET = 444

LANDLOCK_CREATE_RULESET_VERSION = 1 << 0

# ABI level -> (first kernel, feature added at this level)
# Source: Documentation/userspace-api/landlock.rst (kernel docs),
# include/uapi/linux/landlock.h changelog.
ABI_TABLE = [
    (1, "5.13", "filesystem access control (13 FS access rights, "
                "execute/read/write/make_*)"),
    (2, "5.19", "+ LANDLOCK_ACCESS_FS_REFER (file reparenting/linking "
                "across directories)"),
    (3, "6.2",  "+ LANDLOCK_ACCESS_FS_TRUNCATE (truncate(2)/O_TRUNC)"),
    (4, "6.7",  "+ TCP network control: LANDLOCK_ACCESS_NET_BIND_TCP / "
                "CONNECT_TCP (port-based)"),
    (5, "6.10", "+ LANDLOCK_ACCESS_FS_IOCTL_DEV (ioctl on device files)"),
    (6, "6.12", "+ scopes: LANDLOCK_SCOPE_ABSTRACT_UNIX_SOCKET, "
                "LANDLOCK_SCOPE_SIGNAL (IPC isolation)"),
    (7, "6.15", "+ audit support: LANDLOCK_RESTRICT_SELF_LOG_* flags "
                "(denials visible in audit log)"),
]


def probe_abi() -> int:
    """Return the Landlock ABI version, or raise OSError."""
    libc = ctypes.CDLL(None, use_errno=True)
    res = libc.syscall(
        SYS_LANDLOCK_CREATE_RULESET,
        None,                      # attr = NULL
        ctypes.c_size_t(0),        # size = 0
        ctypes.c_uint32(LANDLOCK_CREATE_RULESET_VERSION),
    )
    if res < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return res


def main() -> int:
    try:
        abi = probe_abi()
    except OSError as exc:
        if exc.errno == errno.ENOSYS:
            print("Landlock: NOT available (ENOSYS — kernel < 5.13 or "
                  "CONFIG_SECURITY_LANDLOCK not built)")
        elif exc.errno == errno.EOPNOTSUPP:
            print("Landlock: NOT available (EOPNOTSUPP — built but not "
                  "enabled in the 'lsm=' boot parameter)")
        else:
            print(f"Landlock: unexpected error: {exc}")
            return 2
        print("agent-sandbox behaviour: skip Landlock layer, log a "
              "warning, keep bwrap-only containment.")
        return 1

    print(f"Landlock ABI version: {abi}")
    print(f"Kernel: {os.uname().release}")
    print()
    print("Feature set implied by this ABI:")
    for level, kernel, feature in ABI_TABLE:
        mark = "x" if abi >= level else " "
        print(f"  [{mark}] v{level} (kernel >= {kernel}): {feature}")
    if abi > ABI_TABLE[-1][0]:
        print(f"  [?] v{abi} > v{ABI_TABLE[-1][0]}: newer than this "
              f"probe's table — all listed features available, plus "
              f"unknown newer ones")
    print()
    fs = "yes"
    net = "yes (TCP bind/connect, port-based)" if abi >= 4 else "no"
    scoped = "yes (signals + abstract unix sockets)" if abi >= 6 else "no"
    print("Enforceable by agent-sandbox on this kernel:")
    print(f"  filesystem rules : {fs}")
    print(f"  network rules    : {net}")
    print(f"  IPC scoping      : {scoped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
