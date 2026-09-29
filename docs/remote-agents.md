# Remote agents: one cockpit, agents wherever they live

Epic [#392](https://github.com/RisorseArtificiali/lince/issues/392) · #390 (client mobility) · #391 (multi-host cockpit)

lince's answer to agents running on other machines stays true to its model:
**monitor across hosts, control only through SSH.** The dashboard on your
laptop shows the live state of every agent — local or remote — and when a
remote agent needs you, one keybinding opens an interactive pane into its
host. stdin never crosses a lince transport: control happens on the host
where the agent lives, inside its own Zellij session.

- No daemon listens on the network. The only remote surface is SSH, which
  you already use.
- Credentials stay per-host. The remote agent's keys live on the remote
  machine, inside its own sandbox.
- A dropped network degrades to an explicit **Unreachable** condition —
  never a frozen stale status.

## 1. The remote host

On each machine that will run agents:

1. Install lince (same one-liner as your laptop — the remote host runs the
   full local stack: sandbox, hooks, status files).
2. Launch the dashboard (or just the agent) inside a **named Zellij
   session**. Since #390 the launcher does this by default:

   ```bash
   lince                 # creates or reattaches to session "lince"
   ```

3. Launch agents the usual way (wizard, `N`). Note the instance id
   (`LINCE_AGENT_ID`, shown as the `.state` basename, e.g. `claude-1`):
   the cockpit config below must reference it.

## 2. Your laptop: declare the remote agent

Add an inline table to `[dashboard]` in your dashboard config
(`~/.config/lince-dashboard/config.toml`):

```toml
[dashboard]
[[dashboard.remote_agents]]
name      = "wb-claude"        # dashboard-visible instance name
agent_type = "claude"          # drives the event_map (default: claude)
host      = "maeste@workbox"   # SSH target (alias from ~/.ssh/config works)
session   = "lince"            # Zellij session on the host for Alt+o
agent_id  = "claude-1"         # LINCE_AGENT_ID on the host (default: name)
```

The agent appears in the sidebar with an `@host` suffix and is polled every
dashboard tick (one SSH per declared host, `BatchMode=yes`,
`ConnectTimeout=3`). Status flows through the same 5-state contract as local
agents — attention blink, the attention count, and the attention sound all
fire on your machine.

## 3. Interacting: Alt+o

Select the remote agent (`j`/`k`, `1-9`) and press **Alt+o** (or `Ctrl+o`).
The dashboard opens a floating pane running:

```bash
ssh -t maeste@workbox zellij attach lince     # session configured
ssh -t maeste@workbox                          # no session → plain shell
```

You are now inside the remote session: answer INPUT prompts, approve
PERMISSION requests, read the transcript — all on the host, with the host's
own oversight model. Close the pane (`Alt+f`) when done.

## Notes and limits

- **Kill is refused** for remote agents: they are config-derived. Remove the
  `remote_agents` entry to detach one from the cockpit.
- **State is not saved/restored** for remote agents — sync recreates them
  from config on every reload.
- **Post-reboot**: Zellij resurrection on the host restores the layout and
  re-runs launch commands, but agents restart fresh (see #390's out-of-scope
  note on per-agent `--continue`/`--resume`).
- **Unreachable**: when SSH fails, the agent's row shows `Unreachable`
  instead of its last status; the first successful poll re-arms change
  detection, so no transition is lost on recovery.
- Cross-host agent messaging (`lince-msg` between machines) is a future
  evolution, deliberately out of scope here.
