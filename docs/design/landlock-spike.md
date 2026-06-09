# Landlock spike — feasibility for the bwrap backend (#211)

**Status**: spike complete — recommendation: **GO**
**Date**: 2026-06-10
**Evidence**: live experiments in [`sandbox/spikes/landlock/`](../../sandbox/spikes/landlock/)
(stdlib-only ctypes probe + working demo, run on Fedora 44, kernel
6.19.14-300.fc44.x86_64, Landlock ABI v7 — all checks green, output
captured in the spike README).

Landlock is evaluated as a **defense-in-depth layer inside the existing
bubblewrap backend**, not a new backend: bwrap paints the mount picture,
a Landlock ruleset applied just before the agent `exec` adds a second,
kernel-enforced fence that holds even if something escapes that picture.
Prior art: Codex CLI (Landlock + seccomp as its native Linux sandbox),
landrun/nsjail (compose Landlock with namespaces). microsoft/mxc does
**not** use Landlock (verified, zero references).

---

## Q1 — ABI availability matrix

Kernel → ABI mapping (from kernel `Documentation/userspace-api/landlock.rst`
and `include/uapi/linux/landlock.h`, cross-checked by the live probe):

| ABI | Kernel | Adds |
|-----|--------|------|
| v1 | 5.13 | filesystem access control (execute/read/write/make_* — 13 rights) |
| v2 | 5.19 | `LANDLOCK_ACCESS_FS_REFER` (re-linking/reparenting across dirs) |
| v3 | 6.2 | `LANDLOCK_ACCESS_FS_TRUNCATE` |
| v4 | 6.7 | **TCP network rules**: `LANDLOCK_ACCESS_NET_BIND_TCP` / `CONNECT_TCP` (port-based) |
| v5 | 6.10 | `LANDLOCK_ACCESS_FS_IOCTL_DEV` |
| v6 | 6.12 | scopes: abstract unix sockets + signals (IPC isolation) |
| v7 | 6.15 | audit support (`LANDLOCK_RESTRICT_SELF_LOG_*`) |

Target distros (current and −1, as of June 2026):

| Distro | Kernel | ABI | Enforceable |
|--------|--------|-----|-------------|
| Fedora 44 (current) | 6.19 (live-probed on this box) | **v7** (live-probed: `7`) | fs + TCP net + IPC scopes + audit |
| Fedora 43 (−1) | 6.17 GA | v7 | fs + TCP net + IPC scopes + audit |
| Ubuntu 26.04 LTS (current) | 7.0 | ≥ v7 | fs + TCP net + IPC scopes + audit |
| Ubuntu 24.04 LTS (−1) | 6.8 GA / 6.17 HWE (24.04.4) | **v4** GA / v7 HWE | fs + TCP net (GA); everything (HWE) |

(Sources: Fedora 43 ships 6.17 [packages.fedoraproject.org]; Ubuntu 26.04
LTS ships kernel 7.0 [discourse.ubuntu.com / release notes]; Ubuntu
24.04.4 HWE moved to 6.17 [Phoronix/OMG Ubuntu, Feb 2026].)

**Floor across all targets is ABI v4** → filesystem *and* TCP network
rules are enforceable everywhere we care about. Both Fedora and Ubuntu
enable the `landlock` LSM by default on these releases — but the probe
must never assume: a custom `lsm=` boot line yields `EOPNOTSUPP`.

**Enforce-per-ABI policy (recommended)** — probe once at startup
(`landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION)`,
see `landlock_probe.py`) and cap the handled-access masks to the probed
ABI, exactly as the demo's `fs_rights_for_abi()` does:

- ABI 0 (ENOSYS/EOPNOTSUPP): skip layer, log
  `landlock: not available — bwrap-only containment` (never fail).
- ABI 1–3: fs rules only (mask out REFER/TRUNCATE bits below their ABI);
  log `network rules not enforced (ABI < 4)`.
- ABI ≥ 4: fs + TCP bind/connect rules.
- ABI ≥ 6: optionally add `LANDLOCK_SCOPE_*` later (out of scope here —
  signal scoping can break agent⇄hook interactions and needs its own test
  pass).

Critical Landlock semantics that make this safe: **the handled-access
mask is deny-by-default** — every right listed as handled is denied
unless a rule grants it, and rights *not* handled (because the ABI is
old) are simply not restricted. Best-effort degradation is built into
the API design.

## Q2 — Application point in `sandbox/agent-sandbox`

Today the flow is: `cmd_run()` → `build_bwrap_cmd()` builds a `bwrap`
argv (optionally wrapped in `unshare -U -n -r bash -c <netns setup>` for
paranoid) → `subprocess.run(cmd)` (line ~3893). Two candidate points:

**Option A — `preexec_fn` on the host-side `subprocess.run()`** (restrict
before bwrap even starts). Rejected:

- The ruleset would be built against the **host** mount namespace, but
  bwrap then creates *new* filesystems: `--tmpfs /tmp`,
  `--tmpfs /run/user/<uid>`, etc. A fresh tmpfs is not beneath any
  rule's opened directory FD, so it is **denied by default** — the agent
  could not write `/tmp` at all. (Observed in the spike: even
  `tempfile.gettempdir()` dies once no writable dir is reachable.)
- It would also restrict bwrap itself and, for paranoid, the
  `unshare`/`bash`/`socat` wrapper — trusted plumbing we don't need to
  fence, and whose socket/FS needs would bloat the ruleset.
- `preexec_fn` is documented as not thread-safe with threads in the
  parent — and the credential proxy runs threads in our process.

**Option B — a tiny launcher shim INSIDE the sandbox (recommended)**:
make the shim the last element of the bwrap argv, so the chain is
`bwrap <mounts...> -- <shim> -- <agent argv>`. The shim opens its
directory FDs in the **final** mount namespace (so the bwrap tmpfs and
bind mounts are exactly what the rules attach to), applies the ruleset,
then `os.execvp()`s the agent. Since `agent-sandbox` ro-binds the whole
host `/` into the sandbox, `python3` and the script itself are already
visible inside; the shim can simply be a hidden subcommand of the
single-file script (e.g. `agent-sandbox __landlock-exec --rw <dir> ...
-- <agent argv>`), keeping the zero-extra-files, stdlib-only constraints.
~100 lines of ctypes (the demo's `apply_landlock()` is the core, 60
lines).

**Inheritance — confirmed empirically**: rulesets are inherited across
`fork` + `execve` like `no_new_privs`. The demo restricts the child and
then `subprocess.run()`s a *fresh* `python3`; the grandchild is still
denied outside writes and still allowed inside writes (`[PASS] inherit:`
lines in the captured output). So restricting once in the shim covers
every shell, compiler, and MCP server the agent spawns. Nothing in the
sandbox can lift the fence — rulesets only compose (each
`landlock_restrict_self` can only intersect, never widen).

## Q3 — Network rules vs. the credential proxy

Landlock ABI 4+ network rules are **TCP and port-based, not host-based**
(`LANDLOCK_ACCESS_NET_BIND_TCP` / `CONNECT_TCP` against a port number).
That maps cleanly onto how agent-sandbox already does egress:

- **Normal level + proxy**: the proxy listens on host loopback at an
  ephemeral port (`CredentialProxy.start()`); the agent shares the host
  netns and connects to `127.0.0.1:<port>`. The port is known *before*
  `build_bwrap_cmd()` is called → pass it to the shim as the single
  allowed `CONNECT_TCP` port. **This closes today's biggest normal-level
  gap**: `HTTP_PROXY`/base-URL env rewriting is *cooperative* — a
  malicious tool can ignore the env vars and `connect()` anywhere. With
  Landlock, direct TCP egress is denied at the kernel; the proxy becomes
  mandatory, not advisory. Caveat: port-based means another local
  service on an allowed port number is reachable — acceptable because
  the rule allows only the proxy's ephemeral port (and the proxy's own
  CONNECT allowlist does host filtering).
- **Paranoid level (`unshare_net = true`)**: the wrapper runs
  `unshare -U -n -r`, brings up `lo`, and socat listens on the **fixed
  port 8118** inside the fresh netns, forwarding to the host proxy
  through a bind-mounted unix socket (`proxy-<pid>.sock`). With the shim
  inside bwrap, socat is *outside* the Landlock domain (it execs before/
  alongside bwrap), so it binds 8118 unrestricted; the agent only needs
  `CONNECT_TCP` to port 8118. Note Landlock net rules cover **only TCP**
  — they do not see (and cannot break) the unix-socket bridge, and
  pathname unix-socket `connect()` is not blocked by Landlock fs rights
  either. The composition is conflict-free.
- **Defense-in-depth, not replacement**: Landlock does not restrict UDP,
  ICMP or raw sockets (as of ABI v7). DNS over UDP and QUIC/HTTP-3 are
  uncovered → paranoid still needs `unshare -n`; Landlock adds the TCP
  fence at normal where there is no netns at all.
- **Future `allowed_hosts` policy**: host filtering **stays the proxy's
  job** (it already has `allow_domains` on the CONNECT path). Landlock's
  contribution is port-level deny-by-default for everything that tries
  to bypass the proxy. One intent, two mechanisms: `[network]`
  `allowed_hosts` compiles to proxy allowlist; the proxy port (plus any
  explicitly opened ports) compiles to Landlock `CONNECT_TCP` rules.
- **Bind**: with `handled_access_net` including `BIND_TCP` and no bind
  rules, the agent cannot open listeners at all (demo: `bind` →
  `EACCES`). Dev servers (`npm run dev`) need an explicit
  `allow_bind_ports` policy key at normal level; paranoid should default
  to no bind.

## Q4 — Ordering with bwrap binds (opened FDs vs. mount namespace)

`LANDLOCK_RULE_PATH_BENEATH` rules take an **opened directory FD**
(`O_PATH`); the rule attaches to the *file hierarchy that FD resolves to
at `landlock_add_rule` time*, not to a path string. Consequences:

1. **Open after the mount picture is final.** All rule FDs must be
   opened inside the bwrap mount namespace (Option B guarantees this),
   so rules attach to the bind-mounted views and the bwrap-created
   tmpfs (`/tmp`, `/run/user/<uid>`) the agent actually sees. This is
   exactly what bit the `preexec_fn` variant in Q2.
2. **Bind mounts are transparent** once you open through them: a rule on
   the sandbox-side `/tmp` (tmpfs) or on the bound project dir governs
   accesses through those mounts. No conflict between bwrap binds and
   Landlock observed in the spike — bwrap mounts first, Landlock fences
   second, and mounts created *after* restriction are irrelevant because
   the agent has no CAP_SYS_ADMIN to mount anything.
3. **Compute everything before `landlock_restrict_self()`.** The shim
   itself must resolve paths/EXE lookups up front — after restriction
   the shim is confined too (spike gotcha: `tempfile.gettempdir()`
   fails post-restriction). The shim's last act is `execvp(agent)`,
   which only needs EXECUTE+READ on the agent binary's hierarchy
   (granted by the ro rules on `/usr` etc.).
4. **Rule list = mirror of the bind list.** The shim's rule set is
   mechanical: rw rules for project dir + every `--bind` target
   agent-sandbox already computes (agent config dir, scratch binds,
   extra `--rw`), ro+execute rules for the ro-bound system hierarchy,
   rw on `/tmp` and `/run/user/<uid>` tmpfs, plus `/dev` read/write for
   `/dev/null` & co. No new policy inputs are needed for v1 — it reuses
   the inputs `build_bwrap_cmd()` already has.

## Q5 — Cost

**Runtime (measured, this box, ABI v7, 10 path rules + 1 net rule):**
ruleset create + add rules + `restrict_self` = **60–75 µs** across runs
(`60.1 / 65.5 / 66.0 / 71.6 / 74.1 µs` over 5 consecutive runs; the demo
prints the measurement). One-time at spawn — invisible next to bwrap +
agent startup (hundreds of ms). Per-syscall overhead is a path-walk
check in-kernel; no agent-visible latency at our scale.

**Code surface (estimated from the working demo):**
~100 lines for the ctypes layer (constants + 3 structs + `probe_abi` +
`apply_landlock` — already written and proven in `demo.py`), ~50 lines
for the `__landlock-exec` shim subcommand + argv plumbing in
`build_bwrap_cmd()`, ~20 lines of banner/logging. **≈150–200 lines**
added to `sandbox/agent-sandbox`, zero new dependencies, zero new
installed files.

---

## Recommendation

**GO.** Ship Landlock as default hardening of the bwrap backend:

| Level | Landlock fs | Landlock net (ABI ≥ 4) |
|-------|-------------|------------------------|
| paranoid | **on** (rw = project + binds; ro = system) | **on**: `CONNECT_TCP` → 8118 only; no bind |
| normal | **on** (same rule set) | **on when proxy active**: `CONNECT_TCP` → proxy port (+ `allow_connect_ports`); bind per `allow_bind_ports`. Proxy off → net unrestricted (handled mask = 0) |
| permissive | off | off |

Always probe, never require: ABI 0 → log + continue (bwrap-only); ABI
1–3 → fs only + log that net is not enforced. Surface the enforced state
in the run banner (`landlock    fs+net (ABI 7)` / `fs only (ABI 3)` /
`unavailable`).

**Policy keys for the #201 Config v2 design** — the same intent must
compile to bind mounts *and* Landlock rules (and proxy allowlist):

```toml
[filesystem]
write = ["{project}", "{agent_config}", "/tmp"]   # → bwrap --bind + Landlock rw path rules
read  = ["/"]                                     # → bwrap --ro-bind + Landlock ro+execute rules
# deny-by-default guarantee: anything not listed is neither mounted rw
# nor granted by Landlock — two mechanisms, one intent.

[network]
mode = "proxy"          # "proxy" | "open" | "none"
allowed_hosts = ["api.anthropic.com"]  # enforced by the credential proxy (host-based)
allow_connect_ports = []               # extra Landlock CONNECT_TCP rules (port-based)
allow_bind_ports = []                  # Landlock BIND_TCP rules (dev servers)
```

`mode = "proxy"` ⇒ Landlock allows connect only to the proxy port (8118
under `unshare_net`, the ephemeral host port otherwise) + listed extras;
`mode = "none"` ⇒ handled net mask set, zero rules (full TCP deny);
`mode = "open"` ⇒ net mask not handled (unrestricted). Hosts stay the
proxy's job; ports are Landlock's.

**Next step** (separate task, out of spike scope): implement the
`__landlock-exec` shim in `sandbox/agent-sandbox`, gate one agent at
paranoid, and add a `sandbox/tests/` check mirroring the demo's
assertions.
