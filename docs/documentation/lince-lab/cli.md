# lince-lab CLI Reference

`lince-lab` is one argparse command with **five verb groups**. Verbs are
organized into two levels of help: `lince-lab --help` lists the groups, and
`lince-lab <group> --help` drills into that group's verbs. Every verb is a thin
call to the host-side broker over the unix socket — start it first with
`lince-lab lab broker start`.

## Multi-level help

### Top level

```console
$ lince-lab --help
usage: lince-lab [-h] [-V] [--socket PATH] [--json] [-q] [--timeout SECONDS] <group> ...

Disposable lab-VM substrate for autonomous testing and regression hunting.
Commands are grouped: run `lince-lab <group> --help` to drill into a group's verbs.

positional arguments:
  <group>
    vm                  Manage disposable lab VMs (create/boot/exec/snapshot)
    run                 Run a recipe end-to-end (validate / provision / drive / assert)
    find                Autonomous regression hunting (bisect)
    watch               Observe a VM's terminal (grab / send keys / wait for output)
    lab                 Broker & setup plumbing (broker / doctor / version)

options:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  --socket PATH         broker unix socket
  --json                emit results as JSON
  -q, --quiet           suppress status output
  --timeout SECONDS     per-request socket timeout (s)

groups:
  vm      Manage disposable lab VMs (create/boot/exec/snapshot)
  run     Run a recipe end-to-end (validate / provision / drive / assert)
  find    Autonomous regression hunting (bisect)
  watch   Observe a VM's terminal (grab / send keys / wait for output)
  lab     Broker & setup plumbing (broker / doctor / version)
```

### Group level

```console
$ lince-lab vm --help
usage: lince-lab vm [-h] <verb> ...

positional arguments:
  <verb>
    up        create and start a disposable VM
    down      stop a running VM
    rm        delete a VM
    status    show a VM's status
    list      list all lab VMs
    exec      run a command in the VM (propagates guest exit code)
    copy      copy a file in/out (<name>:<path> marks the VM side)
    snapshot  snapshot create/apply/delete/list
```

Naming a group with no verb prints that group's help and exits **1** — the same
convention the top-level parser uses when no group is given.

## Shared flags

These work before the group name (`lince-lab --socket X vm …`) and on any leaf:

| Flag | Meaning |
|------|---------|
| `--socket PATH` | broker unix socket (default `~/.agent-sandbox/lince-lab.sock`) |
| `--json` | emit the broker result as JSON |
| `-q`, `--quiet` | suppress human status output |
| `--timeout SECONDS` | per-request socket timeout |

## Group: `vm` — manage disposable lab VMs

| Verb | Broker verb(s) | Description |
|------|----------------|-------------|
| `up <name>` | `vm.create` + `vm.start` | create and start a disposable VM |
| `down <name> [-f]` | `vm.stop` | stop a running VM |
| `rm <name> [-f]` | `vm.delete` | delete a VM |
| `status <name>` | `vm.status` | show a VM's status |
| `list` | `vm.list` | list all lab VMs |
| `exec <name> -- argv` | `vm.exec` | run a command in the VM — **propagates the guest exit code** |
| `copy <src> <dst>` | `vm.copy_in` / `vm.copy_out` | copy a file in/out; `<name>:<path>` marks the VM side |
| `snapshot {create,apply,delete,list}` | `snap.*` | manage snapshots |

```console
$ lince-lab vm up lince-lab-demo
started lince-lab-demo

$ lince-lab vm exec lince-lab-demo -- sh -c 'echo hi; exit 3'
hi
$ echo $?
3                       # the guest exit code propagates verbatim

$ lince-lab vm copy ./fix.patch lince-lab-demo:/work/fix.patch
copied ./fix.patch -> lince-lab-demo:/work/fix.patch

$ lince-lab vm snapshot create lince-lab-demo clean
snapshot clean created on lince-lab-demo

$ lince-lab vm status lince-lab-demo --json
{
  "name": "lince-lab-demo",
  "snapshots": ["clean"],
  "status": "running"
}
```

## Group: `run` — run a recipe end-to-end

| Verb | Broker verb | Description |
|------|-------------|-------------|
| `validate <file>` | `recipe.validate` | validate a recipe TOML; data error → exit 65 |
| `recipe <file> [--keep]` | `recipe.run` | run a recipe end-to-end; **propagates the recipe exit code** |
| `presets` | local | list the named presets (`quick` / `bisect` / `networked`) |

```console
$ lince-lab run validate recipes/lince-wizard.toml
recipe lince-wizard is valid

$ lince-lab run recipe recipes/lince-wizard.toml
recipe lince-wizard -> exit 0

$ lince-lab run presets
bisect: Tuned for the autonomous regression loop: base snapshot retained ...
networked: For recipes that legitimately must fetch (npm/pip). Network is ...
quick: Fast, minimal disposable VM for smoke-testing a single command or ...
```

See **[Recipes](recipes.md)** for the schema and **[Presets](presets.md)** for
when to use each preset.

## Group: `find` — autonomous regression hunting

| Verb | Broker verb | Description |
|------|-------------|-------------|
| `bisect <recipe> --good G --bad B --repo-dir D [--out F] [--keep]` | `bisect.run` | binary-search the first-bad commit using a recipe as the verdict oracle |

```console
$ lince-lab find bisect recipes/lince-wizard.toml \
      --good v1.0 --bad HEAD --repo-dir ./my-clone --out bisect.json
first bad commit: c4f1a9e (converged)
```

The full machine-readable result lands in `bisect.json`. See **[Bisect](bisect.md)**.

## Group: `watch` — observe a VM's terminal

| Verb | Broker verb(s) | Description |
|------|----------------|-------------|
| `grab <name> [--program …] [--size CxR]` | `capture.open` + `capture.snapshot` | snapshot the terminal text grid |
| `keys <name> --keys K…` | `capture.open` + `capture.send` | send keys to the terminal |
| `wait <name> --for SUBSTR \| --stable [--stable-ms N]` | `capture.open` + `capture.send` | wait for a substring or grid-stability |

```console
$ lince-lab watch grab lince-lab-demo --program top
top - 12:00:01 up 2 min,  load average: 0.00, 0.00, 0.00
Tasks:  88 total,   1 running,  87 sleeping ...

$ lince-lab watch wait lince-lab-demo --program lince-config quickstart \
      --for "Select agents" --cmd-timeout 30
... (prints the settled grid once the substring appears)
```

`wait` needs exactly one of `--for SUBSTR` (wait until that text appears) or
`--stable` (wait until the grid stops changing within `--stable-ms`). Both use
event-driven deadlines — never a fixed sleep.

## Group: `lab` — broker & setup plumbing

| Verb | Description |
|------|-------------|
| `broker start` | start the broker in-process (uses `LimaBackend`; `FakeBackend` if `LINCE_LAB_FAKE=1`) |
| `broker stop` | stop the broker (removes its socket) |
| `broker status` | ping the broker |
| `doctor` | probe prerequisites (broker reachability + `limactl`) |
| `version` | print the lince-lab version |

```console
$ lince-lab lab broker start &
broker listening on /home/me/.agent-sandbox/lince-lab.sock

$ lince-lab lab doctor
broker: reachable
limactl: True
socket_path: /home/me/.agent-sandbox/lince-lab.sock

$ lince-lab lab version
1.0.0
```

> **Test mode (no KVM):** start the broker with `LINCE_LAB_FAKE=1 lince-lab lab
> broker start` to back it with the in-memory `FakeBackend` — the entire
> CLI → socket → broker path runs with no VM. This is how the unit and
> in-sandbox integration tests exercise the CLI.

## Exit codes

| Code | Meaning |
|------|---------|
| *guest code* | `vm exec` / `run recipe` / `find bisect` propagate the guest/recipe code verbatim |
| `13` | policy denial (`POLICY_DENIED`) |
| `64` | unknown verb (`EX_USAGE`) |
| `65` | malformed recipe / config / protocol (`EX_DATAERR`) |
| `69` | broker unreachable (`EX_UNAVAILABLE`) |
| `1` | a group/verb was named without a sub-verb (help printed) |
