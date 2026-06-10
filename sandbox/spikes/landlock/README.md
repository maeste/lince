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
| `landlock_exec.py` | The launcher shim (prototype of the future `agent-sandbox __landlock-exec` subcommand): runs as the last element of the bwrap argv, opens its rule FDs in the final mount namespace, applies fs (+net if ABI ≥ 4) rules, then `execvp`s the agent argv. Graceful on ABI 0 by default, fail-closed on demand (`--fail-closed` / `LINCE_LANDLOCK_FAIL_CLOSED=1`). Every run emits a single-line JSON **effective-policy record** (`LINCE_EFFECTIVE_POLICY: ` on stderr, optionally to `LINCE_POLICY_RECORD_PATH`) — requested vs enforced, see the design doc. `LINCE_LANDLOCK_FORCE_ABI=N` caps the probed ABI to simulate older kernels. |
| `gate_check.py` | In-sandbox assertion payload run by the shim in place of a real agent binary: proves the fence inside the actual paranoid sandbox (denied write to bwrap's own rw tmpfs `/tmp`, connect allowed only to the socat bridge on 8118, bind denied, inheritance). |
| `paranoid_gate.sh` | **The prototype gate**: gates agent `landlock-demo` at `--sandbox-level paranoid` through the shim using only existing agent-sandbox mechanisms (project-local config + custom agent command — `sandbox/agent-sandbox` is NOT modified). Chain: `unshare`/socat wrapper → bwrap → `landlock_exec.py` → `gate_check.py`. Also captures the effective-policy record from the gated run and asserts `fs_enforced=true`, `net_enforced=true`, `net_limitation="port-only, host-unaware"`. |

## How to run

```bash
python3 sandbox/spikes/landlock/landlock_probe.py
python3 sandbox/spikes/landlock/demo.py

# Q4 composition experiment: same demo inside a bwrap mount namespace
bwrap --ro-bind / / --tmpfs /tmp --dev /dev --proc /proc -- \
  python3 sandbox/spikes/landlock/demo.py

# Paranoid gate prototype: one agent gated at --sandbox-level paranoid
bash sandbox/spikes/landlock/paranoid_gate.sh
```

Exit code 0 = available/all checks pass. On kernels without Landlock the
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
Landlock demo — kernel 6.19.14-300.fc44.x86_64
parent: project dir /tmp/landlock_demo_05j71czg
parent: allowed port 35427, denied port 57021 (both have live listeners)
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

RESULT: ALL CHECKS PASSED
```

(The capture pipe block-buffered the parent's stdout, so the raw capture showed the
parent's header lines after the child's; reordered here to actual execution order.)

Setup-time over 5 consecutive runs: 60.1 / 65.5 / 66.0 / 71.6 / 74.1 µs
(10 `landlock_add_rule` calls + `landlock_restrict_self`).

### Q4 experiment — `demo.py` inside a bwrap mount namespace

The composition question (#211 Q4: bwrap binds vs. Landlock rule FDs) is
answered by running the same demo inside a bwrap sandbox with a **fresh
tmpfs `/tmp`** — the case that breaks the host-side `preexec_fn` variant:

```
$ bwrap --ro-bind / / --tmpfs /tmp --dev /dev --proc /proc -- \
    python3 sandbox/spikes/landlock/demo.py
Landlock demo — kernel 6.19.14-300.fc44.x86_64
parent: project dir /tmp/landlock_demo_92vjy2ai
parent: allowed port 38299, denied port 39993 (both have live listeners)
child: Landlock ABI 7, restricting self...
child: ruleset built + applied in 59.6 us (9 path rules, 1 net rules)
  [PASS] fs: write inside allowed dir succeeds — /tmp/landlock_demo_92vjy2ai/inside.txt
  [PASS] fs: write outside allowed dir denied — errno=EACCES
  [PASS] fs: read /etc (ro rule) still works
  [PASS] net: connect to allowed port 38299 succeeds
  [PASS] net: connect to denied port 39993 blocked — errno=EACCES (listener IS running — denial is Landlock's)
  [PASS] net: bind blocked (no bind rule added) — errno=EACCES
  [PASS] inherit: subprocess (fork+execve) still denied outside write — rc=1
  [PASS] inherit: subprocess can still write inside allowed dir — rc=0

RESULT: ALL CHECKS PASSED
```

All 8 checks pass: the rw rule opened on the bwrap-created tmpfs `/tmp`
works (project dir lives there), denials hold, and inheritance holds —
applying a Landlock ruleset inside a bwrap mount namespace composes with
no conflict, as long as rule FDs are opened after the mount picture is
final.

### `paranoid_gate.sh` — one agent gated at paranoid

The issue's prototype deliverable: agent `landlock-demo` runs at
`--sandbox-level paranoid` (fresh netns + credential proxy + socat
bridge on 8118), with the shim applying Landlock fs + net rules between
bwrap setup and the agent exec:

```
$ bash sandbox/spikes/landlock/paranoid_gate.sh
LINCE_EFFECTIVE_POLICY: {"backend": "bwrap", "requested_level": "paranoid", "requested_fs": {"rw": ["/tmp/landlock_gate_LoteBP"], "ro": ["/"]}, "requested_net": {"connect_ports": [8118], "bind_ports": []}, "landlock_abi": 7, "fs_enforced": true, "net_enforced": true, "net_limitation": "port-only, host-unaware", "applied_before_exec": true, "inherited_by_subprocesses": "by-design; verified by gate_check", "helper_digest": "4f8c5c8da5907e4efdae7f2bf35642f5941dfb967a3be9f4ba064faac44f296d", "bwrap_args_digest": null, "degraded_reason": null}
landlock: fs+net (ABI 7) applied in 47.4 us — rw=['/tmp/landlock_gate_LoteBP'] connect=[8118] bind=[]
gate_check: pid 2 inside paranoid sandbox, project /tmp/landlock_gate_LoteBP
  [PASS] fs: write inside project dir succeeds — /tmp/landlock_gate_LoteBP/inside.txt
  [PASS] fs: write to bwrap rw tmpfs /tmp denied by Landlock — errno=EACCES
  [PASS] fs: read /etc (ro rule) still works
  [PASS] net: connect to proxy bridge port 8118 succeeds — socat listener reached
  [PASS] net: connect to denied port 9 blocked — errno=EACCES (ECONNREFUSED would mean Landlock let it through)
  [PASS] net: bind blocked (no bind rule) — errno=EACCES
  [PASS] inherit: subprocess still denied /tmp write — rc=1

GATE RESULT: ALL CHECKS PASSED
[...agent-sandbox banner...]

gate: effective-policy record from the gated run:
  LINCE_EFFECTIVE_POLICY: {... same record as above ...}
gate: record asserts fs_enforced=true, net_enforced=true, net_limitation="port-only, host-unaware" — OK
```

Two details make this run self-proving:

- bwrap mounts `/tmp` as a fresh **rw** tmpfs at paranoid, so the EACCES
  on the `/tmp` write can only come from Landlock (bwrap would have
  allowed it; a bwrap ro denial would be EROFS);
- the denied port has no listener in the fresh netns, so without
  Landlock the connect would fail ECONNREFUSED — the observed EACCES is
  the LSM's.

The gate uses only existing agent-sandbox mechanisms (project-local
`.agent-sandbox/config.toml` defining the agent's `command` as the shim,
plus a project-local paranoid fragment) — `sandbox/agent-sandbox` is not
modified, keeping this branch conflict-free with the in-flight
credential-proxy and seatbelt PRs. Productizing means moving
`landlock_exec.py` into the script as a hidden `__landlock-exec`
subcommand appended to the bwrap argv by `build_bwrap_cmd()`.

### Degraded path + fail-closed (rpelevin test 3)

`LINCE_LANDLOCK_FORCE_ABI=0` makes the shim behave as on a kernel without
Landlock. By default it stays graceful — the payload still runs, but the
effective-policy record says exactly which boundaries were NOT enforced:

```
$ LINCE_LANDLOCK_FORCE_ABI=0 LINCE_SANDBOX_LEVEL=paranoid \
    python3 sandbox/spikes/landlock/landlock_exec.py \
    --rw /tmp --connect-port 8118 -- echo "payload ran (degraded, fail-open)"
LINCE_EFFECTIVE_POLICY: {"backend": "bwrap", "requested_level": "paranoid", "requested_fs": {"rw": ["/tmp"], "ro": ["/"]}, "requested_net": {"connect_ports": [8118], "bind_ports": []}, "landlock_abi": 0, "fs_enforced": false, "net_enforced": false, "net_limitation": "unavailable", "applied_before_exec": false, "inherited_by_subprocesses": "by-design; verified by gate_check", "helper_digest": "4f8c5c8da5907e4efdae7f2bf35642f5941dfb967a3be9f4ba064faac44f296d", "bwrap_args_digest": null, "degraded_reason": "landlock unavailable (ABI 0 — kernel without Landlock or LSM disabled)"}
landlock: not available — bwrap-only containment
payload ran (degraded, fail-open)
$ echo $?
0
```

With `--fail-closed` (or `LINCE_LANDLOCK_FAIL_CLOSED=1`) the same
degradation refuses to exec — the recommended contract for paranoid
(see the design doc, "Effective policy: requested vs enforced"):

```
$ LINCE_LANDLOCK_FORCE_ABI=0 LINCE_SANDBOX_LEVEL=paranoid LINCE_LANDLOCK_FAIL_CLOSED=1 \
    python3 sandbox/spikes/landlock/landlock_exec.py \
    --rw /tmp --connect-port 8118 -- echo "payload must NOT run"
LINCE_EFFECTIVE_POLICY: {"backend": "bwrap", "requested_level": "paranoid", "requested_fs": {"rw": ["/tmp"], "ro": ["/"]}, "requested_net": {"connect_ports": [8118], "bind_ports": []}, "landlock_abi": 0, "fs_enforced": false, "net_enforced": false, "net_limitation": "unavailable", "applied_before_exec": false, "inherited_by_subprocesses": "by-design; verified by gate_check", "helper_digest": "4f8c5c8da5907e4efdae7f2bf35642f5941dfb967a3be9f4ba064faac44f296d", "bwrap_args_digest": null, "degraded_reason": "landlock unavailable (ABI 0 — kernel without Landlock or LSM disabled)"}
landlock_exec: FAIL-CLOSED — requested filesystem and network boundaries cannot be enforced (Landlock ABI 0); refusing to exec the agent
$ echo $?
1
```

Note the payload is never executed and the record is emitted *before*
the refusal — degraded is only ever explicit + recorded, never silent.
(The forced ABI can only lower the probed value: `min(probed, forced)`.
Forcing 1–3 with net ports requested demonstrates the partial case:
`fs_enforced: true, net_enforced: false, degraded_reason: "network rules
not enforced (ABI n < 4)"` — fail-closed refuses there too.)

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
7. **bwrap composition works** (Q4, tested — see the bwrap-wrapped run
   above): a ruleset applied inside the bwrap mount namespace attaches to
   the bwrap-created tmpfs and bind-mounted views with no conflict.
8. **End-to-end gating at paranoid works** (`paranoid_gate.sh`): the shim
   slots into the real paranoid chain (`unshare`/socat → bwrap → shim →
   agent) and enforces rw-project-only fs plus connect-to-proxy-only net,
   without modifying `sandbox/agent-sandbox`.

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
