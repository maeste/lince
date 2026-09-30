# Remote agents: same wizard, same lifecycle, SSH invisible

Epic [#392](https://github.com/RisorseArtificiali/lince/issues/392) ·
#390 (client mobility) · #391 (multi-host cockpit)

Remote agents in lince have **exactly the same lifecycle as local ones**:
spawned from the `Alt+n` wizard, monitored in the dashboard, opened
interactively on demand, killed with `Alt+x`. The only difference is one
wizard step — **Location** — where you pick `this machine` or `remote
(SSH)` and type the host. Everything else, including all SSH plumbing,
is hidden.

- No daemon listens on the network. The only remote surface is SSH, which
  you already use.
- Credentials stay per-host: the remote agent's keys live on the remote
  machine, inside its own sandbox.
- A dropped network degrades to an explicit **Unreachable** condition —
  never a frozen stale status.

## The only two prerequisites

1. **lince is installed on the remote host** (same one-liner as your
   laptop). The spawn step verifies this and fails with a clear message
   otherwise.
2. **Your machine can SSH to the host with key auth** — if `ssh host`
   gets you a shell, remote agents work.

## Creating a remote agent (Alt+n)

The wizard flow is unchanged until the last step:

```
┌─ New Agent Wizard ─────────────────────────────┐
│  Step 6/7: Location                            │
│  > this machine                                │
│    remote (SSH)                                │
│  [j/k] Choose  [type] SSH host  [Enter] Next   │
└────────────────────────────────────────────────┘
```

Pick `remote (SSH)` (`j`/`Down` or just start typing) and enter the SSH
target (`user@host` — aliases from `~/.ssh/config` work). Confirm shows
the summary with `Host: <host> (remote)`; `Enter` launches.

Under the hood lince opens a **detached Zellij session dedicated to the
agent** on the remote host (`lince-<id>`) and runs the same launch command
line a local agent would get — sandbox wrapper, provider env bundle, hooks.
The agent appears in the dashboard immediately; a failed launch removes it
and reports why.

## Same lifecycle, every path

| Action | Local agent | Remote agent |
|--------|-------------|--------------|
| Status | `.state` files, local | same `.state` files, polled over SSH (one SSH per host per tick) |
| Attention (R→I/P) | local | local — attention fires on *your* machine |
| Open (`Alt+o`) | focus the pane | floating pane with `ssh -t host zellij attach <session>` — you're inside the remote session |
| Kill (`Alt+x`) | pane closed | the agent's session is killed on its host over SSH |
| Quit dashboard | agents stop with the session | agents keep running — relaunch `lince` and restore reattaches to their live sessions instead of spawning duplicates |
| Host down | — | row shows `Unreachable` (never the stale status); first poll after recovery re-arms change detection |

## Notes and limits

- Cross-host agent messaging (`lince-msg` between machines) is a future
  evolution, deliberately out of scope.
- If the remote agent's process exits, its session disappears and the row
  turns `Stopped` on the next tick — same signal as a local pane closing.
- Project directory browsing (Tab-completion) is local-only; for a remote
  agent type the path as it exists **on the remote host**.
