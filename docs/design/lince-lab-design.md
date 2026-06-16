# lince-lab — Disposable Lab-VM Substrate + Autonomous Bisect

Epic: [#262](https://github.com/RisorseArtificiali/lince/issues/262) · Sub-issues: #252–#261
Status: FINAL design (synthesized from the v1 blueprint + Lima/`ht` research) · File: `docs/design/lince-lab-design.md`

## 0. Problem statement

Agents that drive lince — running the quickstart wizard, checking `install.sh`
idempotency, hunting a regression across commits — need a **disposable, isolated
substrate** they can create, drive, snapshot, reset, and destroy without ever
touching the host filesystem or the user's real Lima VMs, and without being
trusted to relax their own isolation. Today there is no such substrate: an agent
either runs commands directly on the host (no isolation, no clean reset) or has
no terminal-level oracle at all (cannot drive an interactive TUI deterministically,
cannot bisect a flaky wizard).

`lince-lab` adds: a **host-side broker** the agent commands over a narrow unix
socket; a **Backend** seam with a real `LimaBackend` (QEMU on Linux) and an
in-memory `FakeBackend` (all logic testable with no VM); a **recipe** contract
(TOML: image + network posture + one staged workspace + ordered steps + a
mandatory `[assert]` block) that doubles as the **verdict oracle** for an
autonomous **bisect** loop; and a deterministic terminal-capture layer (`ht`
inside the VM, event-driven `wait_for_*` primitives, no fixed sleeps). One
argparse CLI (`lince-lab`), one skill, no MCP.

This document is the authoritative design. It is written for **both audiences**:
a user deciding whether/how to use lince-lab, and an agent driving it through the
skill. The decisions below are recorded as ADR-01..ADR-10 (titles follow the
blueprint §10). They are not relitigated in implementation; deviations from the
blueprint are noted inline with a one-line justification.

### 0.1 Design invariants

These hold across every backend, recipe, and code path. Each is enforced
mechanically (policy gate, validation, or test), not by prose.

| #  | Invariant | Enforced by |
|----|-----------|-------------|
| L1 | **The agent never sees the VM filesystem.** It observes the VM only through broker verbs (status / exec result / copied-out file / terminal grid). There is no raw-shell / interactive-passthrough verb. | closed verb whitelist (ADR-07) + broker dispatch |
| L2 | **The client is never trusted.** Every policy decision (template contents, copy-in path bounds, secret stripping, VM-name namespace, network posture) is evaluated **broker-side** from the recipe's declared needs, not from client-supplied data. | `policy.check(verb, args, ctx)` at the top of every dispatch (ADR-05) |
| L3 | **No host credentials cross into the VM.** Secret-shaped env keys are stripped before forwarding; host secret dirs (`~/.ssh`, `~/.config/lince`, `~/.aws`, …) are never staged. | proxy/policy gate (ADR-05), tested |
| L4 | **Default-deny network.** A recipe with `[network] mode = "deny"` (the default) gets no egress; `mode = "allow"` is rejected at validation unless it carries a non-empty `allow_hosts`/`allow_ports` allowlist. | recipe validation (ADR-06) + per-recipe egress rule (ADR-05) |
| L5 | **Exit codes are the signal.** A failing guest command / recipe is **not** an internal error — `limactl shell` propagates the guest exit code, the broker carries it verbatim, the CLI exits with it. This is what makes oracle-chaining and bisect work. | `ExecResult.exit_code` passthrough (ADR-08) |
| L6 | **Determinism, no fixed sleeps.** Terminal synchronization is event-driven (`wait_for_substring` / `wait_for_stable` over `ht` snapshot/output events) with monotonic deadlines; capture steps without a `[sync]` block fail validation. | `capture.py` wait primitives (ADR-04) + recipe validation (ADR-06) |
| L7 | **Security invariants are non-overridable.** No host mounts, no credential injection, and the `lince-lab-*` VM-name namespace are policy, not config — presets and the config file cannot weaken them. | `config.py` carries only resource/network/lifecycle knobs (ADR-09) |
| L8 | **Logic is VM-free testable.** Every module above the substrate glue runs against `FakeBackend`; only `LimaBackend` needs `/dev/kvm`. The same contract suite runs against both backends. | Backend ABC + `FakeBackend` (ADR-02) |

## 1. ADR-01: Broker-mediated topology

**Decision.** The agent runs inside the bubblewrap sandbox and commands a
**host-side broker** over a narrow `AF_UNIX` `SOCK_STREAM` socket at
`~/.agent-sandbox/lince-lab.sock` (the sandbox runtime dir, so the existing bind
idiom applies). The broker talks to the backend (Lima VMs as host-level siblings).
The agent never has the VM filesystem mounted; it observes the VM only through
broker verbs.

**Topology.**

```
agent (in bwrap sandbox)
   │  newline-delimited JSON over unix socket
   ▼
broker (host process)  ──►  Backend  ──►  Lima VM (QEMU)  /  FakeBackend (in-memory)
```

**Why.** Putting the broker host-side keeps the VM-control surface (`limactl`,
QEMU, snapshot files, the user's other VMs) entirely outside the agent's reach
(L1, L2). The socket is the only channel; a closed verb whitelist (ADR-07) bounds
what can be asked. The socket is created `0600`, owner-only; the broker is
single-threaded with a per-VM lock, so concurrent agents serialize rather than
race a VM.

**Capture channel.** Most verbs are one request → one response. The exception is
`capture.open`, which **upgrades the same connection** to a bidirectional line
stream: subsequent `capture.send` / `capture.snapshot` requests and asynchronous
`{"event": ...}` frames flow over it until the channel closes.

**Implications for users.** You start the broker once (`lince-lab lab broker
start`); the CLI and the skill both speak to it. You never run `limactl` directly
for lab VMs.

## 2. ADR-02: Backend abstraction (Lima + Fake)

**Decision.** All VM operations go through a single `Backend` ABC
(`lince_lab/backend.py`). Two implementations:

- **`LimaBackend`** (`lima_backend.py`) — real; shells `limactl`. KVM-only glue.
- **`FakeBackend`** (`fake_backend.py`) — in-memory, deterministic, no I/O.

The ABC surface (dataclasses `VmState`, `VmStatus`, `ExecResult`; a
`CaptureChannel` duplex):

| Group | Methods |
|-------|---------|
| lifecycle | `create`, `start`, `stop`, `delete`, `status`, `list` |
| exec / files | `exec` (returns `ExecResult`, exit code propagates), `copy_in`, `copy_out` |
| snapshots | `snapshot_create`, `snapshot_apply`, `snapshot_delete`, `snapshot_list` |
| capture | `open_capture(name, argv, cols, rows) -> CaptureChannel` |

**Why.** The seam is the load-bearing testability decision (L8). Every higher
layer — broker, policy, recipe runner, bisect search, capture wait primitives —
is pure logic over `Backend`, so the entire flow is exercised against
`FakeBackend` with no VM. `FakeBackend` is a *faithful* stand-in: a single
contract test suite runs against both backends for every method whose semantics
are backend-independent (status transitions, snapshot round-trip, exec
exit-code passthrough, copy round-trip).

`FakeBackend` is programmable: tests register `on(name, argv_pattern, ExecResult
| callable)` to script guest commands; a callable receives the virtual filesystem
and may mutate it (modelling an installer writing a marker file) — this is how
`install.sh` idempotency and bisect "regression appears at commit X" are tested
without a VM. `snapshot_apply` deep-copies fs+state back, so reset correctness is
assertable.

**Why a seam and not just Lima.** Beyond testability, the seam keeps a future
macOS `vz` backend a drop-in: only this file's glue is platform-specific.

## 3. ADR-03: Lima/QEMU substrate + snapshot-based reset

**Decision.** The real substrate is **Lima** driving **QEMU** (the only Linux
vmType; `vz` is macOS-only and does not support snapshots). VMs are created
`--plain` with `mounts: []`, qcow2 disks, and a pinned Lima version. Reset
between bisect candidates uses `limactl snapshot`.

**`limactl` mapping** (`lima_backend.py`, 1:1 with the verified cheat-sheet):

| Backend method | `limactl` invocation |
|----------------|----------------------|
| `create` | `limactl create --name N -` (template on stdin) |
| `start` | `limactl start N -y` (`-y` = `--tty=false`, for automation) |
| `stop` / `delete` | `limactl stop N [-f]` / `limactl delete N [-f]` |
| `status` / `list` | `limactl list N --json` → `VmState` |
| `exec` | `limactl shell [--workdir W] N -- argv`; **returns the guest exit code** |
| `copy_in` / `copy_out` | `limactl copy [-r] SRC N:DST` / `N:SRC DST` |
| `snapshot_*` | `limactl snapshot create\|apply\|delete\|list N --tag TAG` |

**Why QEMU snapshots.** On Linux/QEMU, `limactl snapshot create/apply` works in
both running (QEMU monitor `savevm`/`loadvm`) and stopped (`qemu-img snapshot`)
states and requires `qemu-img` + qcow2 disks. The bisect loop builds one base
snapshot after provisioning, then `snapshot_apply`s it before each candidate — a
fast, identical clean reset per probe (ADR-08).

**Why `--plain` + `mounts: []`.** Plain mode ignores host mounts and
port-forwarding, so no host directory or secret reaches the guest by default
(L3); the one staged workspace arrives via `copy_in` (policy-bounded, ADR-05).
Networking is severed guest-side (default-deny, ADR-05) because Lima has no
single "disable user-mode net" YAML flag.

**Prerequisites.** `limactl`, `qemu-img`, `/dev/kvm` access. `lince-lab lab
doctor` probes these; the KVM-only oracles skip cleanly when `/dev/kvm` is absent.

## 4. ADR-04: `ht` for deterministic terminal capture

**Decision.** Terminal capture uses **`ht`** (headless terminal, a single static
Rust binary) run **inside the VM** wrapping the driven program, controlled over
line-delimited JSON. `pyte` is the documented fallback (same VM-side PTY-owner
architecture). `ht` is installed by a provision step in capture recipes (pinned tag).

**API** (`lince_lab/capture.py`, wrapping a `CaptureChannel`):

| Primitive | Behavior |
|-----------|----------|
| `send_keys(keys)` / `input(payload)` | inject keystrokes |
| `snapshot() -> Grid` | take a terminal snapshot; `Grid.text` (one line per row) is the assertion surface |
| `wait_for_substring(needle, timeout_s)` | block on `output` events, re-snapshot, check; monotonic deadline; raise `CaptureTimeout` on deadline — **no sleep** |
| `wait_for_stable(debounce_ms, timeout_s)` | snapshot, block for `debounce_ms` of event-silence; any `output` resets the window; return when silent — **no sleep** |

**Why event-driven, not sleeps.** Fixed `sleep`s make a wizard-driving test both
slow and flaky. The two wait primitives are the deterministic synchronization
the design demands (L6): every keypress in a capture step is preceded by
`wait_for_substring` (the expected prompt) then `wait_for_stable` (the screen
settled). They are unit-tested against a scripted `FakeCaptureChannel`: a
"needle appears after N output bursts" script asserts `wait_for_substring`
returns; a "busy then quiet" script asserts `wait_for_stable` returns only after
silence; a "never settles" script asserts the timeout fires.

**Why `ht` over alternatives.** `ht` is a single static binary (trivial to pin
and install in a disposable VM), exposes a clean JSON snapshot/event protocol,
and owns the PTY so it captures the real rendered grid (not a raw byte stream).
`tmux` would add a server and a control-protocol surface; raw PTY scraping loses
the rendered grid. `pyte` stays documented as the in-process fallback.

## 5. ADR-05: Deny-by-default network + per-recipe allowlist; no host credential injection

**Decision.** Network is **deny by default**. A recipe opts into egress only via
an explicit `[network] mode = "allow"` with a non-empty `allow_hosts`/`allow_ports`
allowlist, compiled **broker-side** into the guest egress rule. Host credentials
are never injected into the VM.

**Policy enforcement points** (`policy.py`, evaluated broker-side only — L2):

1. **`vm.create`** — the template YAML is **rebuilt server-side** from the
   recipe's declared needs, never accepted from the client. Policy forces
   `plain: true`, `mounts: []`, the net-cut boot provision, and
   `ssh.loadDotSSHPubKeys: false`. The client cannot inject mounts or
   out-of-allowlist images.
2. **Network** — deny-by-default; the recipe's allowlist is the only widening
   (L4). `recipe.run` with `mode` other than `deny` and an empty allowlist is
   refused at validation (ADR-06).
3. **`vm.copy_in`** — the host path must resolve under the recipe's declared
   `[workspace].host_dir`; any `..`/absolute escape → `POLICY_DENIED`. Host
   secret dirs are on a denylist and never staged (L3).
4. **Credentials** — `env` keys matching the secret pattern (`*_TOKEN`, `*_KEY`,
   …) are stripped from `vm.exec` before forwarding (L3).
5. **Name namespace** — every VM name is forced into the `lince-lab-<recipe>`
   prefix; the broker refuses to operate on any instance outside it, so it can
   never touch a user's pre-existing Lima VMs (L2, L7).

Enforcement is one `policy.check(verb, args, recipe_ctx)` call at the top of
every dispatch; it raises `PolicyDenied` (→ exit 13). Because policy is pure, it
is unit-tested exhaustively against `FakeBackend` (no VM).

**Why.** A test substrate that an untrusted agent drives must fail *closed*: the
agent declares intent (a recipe), and the host decides what that intent is
allowed to become. Trusting client-supplied template YAML or copy-in paths would
let the agent mount `~/.ssh` or open arbitrary egress — exactly the boundary
lince-lab exists to hold.

## 6. ADR-06: Recipe contract

**Decision.** A recipe is a TOML file (`tomllib`, read-only — no edit surface, so
no `tomlkit` at runtime). It declares *needs*, never mechanism; the broker builds
the template. `[recipe]`, `[vm]`, `[workspace]`, and `[assert]` are required;
`[sync]` is required when any step has `capture = true`; `[assert]` must carry
≥ 1 assertion.

**Schema** (tables, as implemented in `recipe.py`):

| Table | Keys | Notes |
|-------|------|-------|
| `[recipe]` | `name`, `description`, `version` | identity; `name` seeds the `lince-lab-<name>` VM |
| `[vm]` | `image`, `cpus`, `memory`, `disk` | `image` must be in the config allowlist; template built server-side |
| `[network]` | `mode` (`deny`\|`allow`), `allow_hosts`, `allow_ports` | `allow` requires a non-empty allowlist (L4) |
| `[workspace]` | `host_dir`, `guest_dir` | the ONE host dir staged; must resolve under the recipe dir |
| `[[provision]]` | `mode`, `script` | baked once into the `base-clean` snapshot |
| `[[step]]` | `name`, `run` (exec) **or** `capture=true` + `program` + `size` + `keys` | ordered |
| `[assert]` | `exit_code`, `grid_contains`, `grid_absent`, `file_exists` | ≥ 1 required |
| `[sync]` | `wait_for`, `stable_ms`, `timeout_s` | required iff any capture step; no fixed sleeps (L6) |

**Validate** (`recipe.validate` → exit 0 / 65): required tables present;
≥ 1 assertion; every capture step has `[sync]`; `allow` carries an allowlist;
`host_dir` resolves under the recipe dir; image in the config allowlist (when a
config is supplied). Pure Python, fully unit-tested.

**Run** (`recipe.run`): validate → broker builds the policy-forced template →
`create` + `start` → run `[[provision]]` → `snapshot_create("base-clean")` →
`copy_in` the workspace → for each step (capture: open channel, then per key
`wait_for_substring` → `wait_for_stable` → `send_keys`; exec: run argv, capture
exit) → evaluate `[assert]` against the final settled grid + `test -f` for
`file_exists` → return 0 if all pass else the failing code; `delete` unless `--keep`.

**Why a mandatory `[assert]` + `[sync]`.** A recipe with no assertion is not an
oracle — it can never be "bad", so bisect is meaningless against it; validation
rejects it. `[sync]` is mandatory for capture steps because that is where
non-determinism would otherwise creep in (L6).

## 7. ADR-07: CLI shape

**Decision.** One argparse single-file CLI (`lince-lab`), mirroring
`lince-config`; **no MCP**. Verbs are organized into **five top-level groups**
with two-level subparsers, giving the grouped multi-level help: `lince-lab
--help` lists the groups, `lince-lab <group> --help` drills into a group's verbs.
The CLI is a thin front-end — every verb is a small `cmd_*` handler that calls
`BrokerClient`. The CLI's verb surface is exactly the broker whitelist; there is
no raw-shell verb (L1).

> **Deviation from blueprint §4.** The blueprint table heading says "Top-level
> groups (4)" but enumerates five rows (`vm`, `run`, `find`, `watch`, `lab`); the
> implementation ships **five** groups. Justification: `lab` (broker/doctor/version
> plumbing) is a distinct concern from `watch` (terminal observation) and the
> blueprint's own row list already separates them — the "4" was a typo, "5" is the
> intended and implemented shape.

| Group | Purpose (top-level `--help`) | Verbs |
|-------|------------------------------|-------|
| `vm` | manage disposable lab VMs | `up`, `down`, `status`, `list`, `exec`, `copy`, `snapshot {create,apply,delete,list}`, `rm` |
| `run` | run a recipe end-to-end | `validate`, `recipe`, `presets` |
| `find` | autonomous regression hunting | `bisect` |
| `watch` | observe a VM's terminal | `grab`, `keys`, `wait` |
| `lab` | broker & setup plumbing | `broker {start,stop,status}`, `doctor`, `version` |

**Closed verb whitelist** (`protocol.py`): the agent CLI maps only to
`vm.{create,start,stop,delete,status,list,exec,copy_in,copy_out}`,
`snap.{create,apply,delete,list}`, `recipe.{validate,run}`, `bisect.run`,
`capture.{open,send,snapshot}`, `ping`. Anything else → `UNKNOWN_VERB` (exit 64).

**Why two-level subparsers.** Flat verbs would make `--help` an undifferentiated
list of ~20 entries. Grouping by concern (lifecycle vs recipe vs bisect vs
observe vs plumbing) lets a user — or an agent — find the right verb from the
group blurb, and keeps each group's help focused.

## 8. ADR-08: Exit-code propagation as the oracle/bisect signal

**Decision.** The CLI exit code is **always** the broker response's exit code.
A failing guest command or recipe is not an internal error — it is the signal.

| Surface | Exit code |
|---------|-----------|
| `vm exec` / `run recipe` / `find bisect` | the **guest/recipe** code, verbatim (L5) |
| policy denial | 13 (`POLICY_DENIED`) |
| unknown verb | 64 (`EX_USAGE`) |
| malformed recipe/config/protocol | 65 (`EX_DATAERR`) |
| broker unreachable | 69 (`EX_UNAVAILABLE`) |

`limactl shell` propagates the guest command's exit code (verified in Lima
source: `shell.go` → `sshCmd.Run()` → `HandleExitError` → `os.Exit(ExitCode())`).
The broker carries it in `ExecResult.exit_code`; the CLI returns it. A `make
test` returning 1 in the VM → `lince-lab vm exec … ` exits 1.

**Why this is load-bearing.** The bisect verdict *is* this exit code: recipe exit
0 ⇒ "good", nonzero ⇒ "bad". The oracle-chaining convention (each
`scripts/lince-lab/ci/NN-*.sh` exits 0 only on success, triggering `NN+1`) is the
same mechanism. If lince-lab swallowed guest failures into a generic error, both
would break.

## 9. ADR-09: Config + presets

**Decision.** Config is **optional**: sane defaults baked in `config.py`
(`DEFAULTS`) so a non-expert runs `lince-lab run recipe X` with zero config. A
user file at `~/.config/lince-lab/config.toml` (created by `install.sh` only if
absent) overlays the defaults (`tomllib`). Three named **presets** select
resource/network/lifecycle knobs.

**Defaults** include: socket path, `lima_version` pin, `capture_tool = "ht"`,
`grid_size = "80x24"`, default `cpus`/`memory`/`disk`, `network.mode = "deny"`,
and an `images` allowlist mapping a short name (`fedora`, `ubuntu`) to a pinned
source — a recipe can only request a known image.

**Presets** (`run presets` lists them):

| Preset | When to use | Knobs |
|--------|-------------|-------|
| `quick` | smoke-test a single command/recipe | 1 CPU / 1GiB / 10GiB, deny, no base snapshot, auto-delete |
| `bisect` | the autonomous regression loop | 2 CPU / 2GiB, deny, **base snapshot retained** for fast reset, long step timeout |
| `networked` | recipes that must fetch (npm/pip) | 2 CPU / 2GiB, `allow` but only the recipe's explicit allowlist, no host credentials |

**Why presets, and why they cannot weaken security.** Presets exist so the common
postures are one word, not five knobs. Crucially, they carry **only**
resource/network/lifecycle keys — the security invariants (no host mounts, no
credential injection, the `lince-lab-*` name namespace) are policy in `policy.py`,
not config, and therefore **non-overridable** through this layer (L7). `networked`
widens egress only to the recipe's own allowlist; it can never inject credentials
or drop the metadata-endpoint block.

## 10. ADR-10: Pixel capture is an OPTIONAL layer over the text grid

**Decision.** The **text grid** (`Grid.text`, one line per terminal row) remains
the canonical assertion surface — every oracle assertion (`grid_contains`,
`grid_absent`) is a substring check on it. A pixel/PNG renderer (grid → image) is
implemented as an **optional output layer** behind an **optional Pillow
dependency** (`lince_lab/render.py`, surfaced via `watch grab --png NAME`):

- **Pillow present** → the captured grid is rendered to a real PNG under the
  server-derived artifacts root (`<artifacts>/NAME.png`); oracle 05 asserts the
  PNG signature is valid.
- **Pillow absent** → there is **no fake PNG**. The renderer refuses
  (`grid_text_to_png` raises) and the CLI writes the grid text to
  `<artifacts>/NAME.txt` as the honest capture artifact instead.

**Why optional, not core.** A PNG adds nothing to *correctness* (text substring
checks are deterministic and host-stable) and a lot to the dependency/comparison
surface (image diffing, font/render determinism). Keeping it Pillow-gated means a
clean checkout with no Pillow still captures (as text), and only hosts that want
pixels pull the extra dependency.

**Why it stays a clean layer.** The renderer consumes the same `Grid.text` the
wait primitives already produce — an independent output layer that needed no
change to the broker, the recipe contract, or the wait primitives.

---

## Appendix A — file layout (reference)

| Path | Role |
|------|------|
| `lince-lab/lince-lab` | argparse front-end (`cmd_*`, `build_parser`, `main`) |
| `lince-lab/lince_lab/` | importable logic package (absolute imports only) |
| `lince-lab/recipes/` | shipped recipe library (installed to share) |
| `lince-lab/templates/` | Lima YAML skeleton |
| `lince-lab/skills/lince-lab/` | the skill (`SKILL.md` + `references/`) |
| `lince-lab/tests/` | `unittest` files, FakeBackend-driven |
| `scripts/lince-lab/ci/NN-*.sh` | real-VM oracles (KVM host / CI only) |

Installed layout (`install.sh` targets): CLI → `~/.local/bin/lince-lab`;
package + recipes + templates → `~/.local/share/lince/lince-lab/{lince_lab,recipes,templates}/`;
skill → `~/.claude/skills/lince-lab/`; default config → `~/.config/lince-lab/config.toml`
(only if absent); runtime broker socket → `~/.agent-sandbox/lince-lab.sock`.

## Appendix B — user & agent docs

- User docs: `docs/documentation/lince-lab/` — `index.md`, `cli.md`, `recipes.md`,
  `presets.md`, `bisect.md` (linked from `docs/documentation/_sidebar.md`).
- Agent playbook: `lince-lab/skills/lince-lab/SKILL.md` + `references/`.
