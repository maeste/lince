# Landlock spike — probe + demo (#211)

Live experiments backing the feasibility doc at
[`docs/design/landlock-spike.md`](../../../docs/design/landlock-spike.md).
Both scripts are **stdlib-only** (ctypes), Python 3.11+, no external
dependencies — the same constraint as `sandbox/agent-sandbox`.

## Files

| File | What it does |
|---|---|
| `landlock_probe.py` | Queries the kernel's Landlock ABI version via `landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION)` and prints the implied feature set. This is the startup probe agent-sandbox would run to decide what to enforce. |
| `demo.py` | Working self-restriction demo: a child process applies a Landlock ruleset (rw beneath a temp project dir, ro+execute on system paths, TCP connect allowed only to one port), then proves the fence holds — including across `fork`+`execve` into a fresh subprocess. |

## How to run

```bash
python3 sandbox/spikes/landlock/landlock_probe.py
python3 sandbox/spikes/landlock/demo.py
```

Exit code 0 = available/all checks pass. On kernels without Landlock both
scripts degrade gracefully (clear message, no crash) — the same pattern
agent-sandbox would use.

## Captured output (Fedora 44, kernel 6.19.14-300.fc44.x86_64, 2026-06-10)

### `landlock_probe.py`

```
Landlock ABI version: 7
Kernel: 6.19.14-300.fc44.x86_64

Feature set implied by this ABI:
  [x] v1 (kernel >= 5.13): filesystem access control (13 FS access rights, execute/read/write/make_*)
  [x] v2 (kernel >= 5.19): + LANDLOCK_ACCESS_FS_REFER (file reparenting/linking across directories)
  [x] v3 (kernel >= 6.2): + LANDLOCK_ACCESS_FS_TRUNCATE (truncate(2)/O_TRUNC)
  [x] v4 (kernel >= 6.7): + TCP network control: LANDLOCK_ACCESS_NET_BIND_TCP / CONNECT_TCP (port-based)
  [x] v5 (kernel >= 6.10): + LANDLOCK_ACCESS_FS_IOCTL_DEV (ioctl on device files)
  [x] v6 (kernel >= 6.12): + scopes: LANDLOCK_SCOPE_ABSTRACT_UNIX_SOCKET, LANDLOCK_SCOPE_SIGNAL (IPC isolation)
  [x] v7 (kernel >= 6.15): + audit support: LANDLOCK_RESTRICT_SELF_LOG_* flags (denials visible in audit log)

Enforceable by agent-sandbox on this kernel:
  filesystem rules : yes
  network rules    : yes (TCP bind/connect, port-based)
  IPC scoping      : yes (signals + abstract unix sockets)
```

### `demo.py`

```
child: Landlock ABI 7, restricting self...
child: ruleset built + applied in 67.2 us (9 path rules, 1 net rules)
  [PASS] fs: write inside allowed dir succeeds — /tmp/landlock_demo_05j71czg/inside.txt
  [PASS] fs: write outside allowed dir denied — errno=EACCES
  [PASS] fs: read /etc (ro rule) still works
  [PASS] net: connect to allowed port 35427 succeeds
  [PASS] net: connect to denied port 57021 blocked — errno=EACCES (listener IS running — denial is Landlock's)
  [PASS] net: bind blocked (no bind rule added) — errno=EACCES
  [PASS] inherit: subprocess (fork+execve) still denied outside write — rc=1
  [PASS] inherit: subprocess can still write inside allowed dir — rc=0
Landlock demo — kernel 6.19.14-300.fc44.x86_64
parent: project dir /tmp/landlock_demo_05j71czg
parent: allowed port 35427, denied port 57021 (both have live listeners)

RESULT: ALL CHECKS PASSED
```

Setup-time over 5 consecutive runs: 60.1 / 65.5 / 66.0 / 71.6 / 74.1 µs
(10 `landlock_add_rule` calls + `landlock_restrict_self`).

## What this proves

1. **Availability**: this Fedora 44 box exposes Landlock ABI v7 — full fs
   + TCP-port network rules + IPC scoping + audit.
2. **Filesystem fence works**: deny-by-default for every handled access
   right; only the explicitly allowed project dir is writable, system
   paths stay readable/executable via ro rules. The denial is `EACCES`
   (clean error an agent can surface), not a crash.
3. **Network fence works and is provably Landlock's**: the denied port has
   a *live listener*, so the `EACCES` (instead of `ECONNREFUSED`) can only
   come from the LSM. `bind()` is also denied since no bind rule was added.
4. **Inheritance across exec**: a `subprocess.run()` launched *after*
   `landlock_restrict_self()` is still confined (denied outside, allowed
   inside). This is the property that makes Landlock useful for
   agent-sandbox: restrict once in the launcher, every agent subprocess
   (shells, compilers, MCP servers) inherits the fence.
5. **Cost is negligible**: ~60–75 µs one-time setup at spawn;
   no measurable per-syscall overhead concern at our scale.
6. **Graceful degradation is trivial**: a single probe call distinguishes
   ENOSYS / EOPNOTSUPP / ABI level; the enforcement code simply caps the
   handled-access mask to what the probed ABI supports.

## Gotchas found while building this (feed into implementation)

- `struct landlock_path_beneath_attr` is `__attribute__((packed))` — in
  ctypes you need `_pack_ = 1` (and `_layout_ = "ms"` to silence the
  Python 3.14 deprecation warning).
- Rules reference **opened directory FDs** (`O_PATH`), resolved in the
  *current mount namespace at open time* — ordering with bwrap binds
  matters (see Q4 in the design doc).
- Don't call `tempfile.gettempdir()` after restriction: it probes for a
  writable temp dir by creating files and finds none — amusing proof the
  fence works, but it breaks code that runs after restriction. The real
  launcher must compute paths *before* `landlock_restrict_self()`.
