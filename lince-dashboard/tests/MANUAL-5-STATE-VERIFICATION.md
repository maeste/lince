# Manual 5-State Verification — lince-dashboard (m-15 / LINCE-123)

End-to-end procedure to verify the 5-state status model with every supported
agent. Run these scenarios after any change that touches hooks, the status
pipeline (`dashboard.rs::poll_status_files`, `agent.rs`), or `types.rs`.

## Setup (run once)

```bash
# Build + install dashboard
cd /home/maeste/project/lince/lince-dashboard
PATH="$HOME/.cargo/bin:$PATH" $HOME/.cargo/bin/cargo build \
    --manifest-path plugin/Cargo.toml --target wasm32-wasip1
bash install.sh    # installs hooks, skill, WASM, configs
zellij --layout layouts/lince.kdl
```

Pre-flight checks:
- `tail -F /tmp/lince-dashboard/hook-debug.log` in a side terminal to watch hook emissions
- `tail -F /tmp/lince-dashboard/wrapper-debug.log` for wrapper events
- `tail -F /tmp/lince-dashboard/*.state` (or `ls -la`) to spot file-fallback writes

Canonical states (drives both color and label in the agent table):

| State              | Label        | Color (ANSI) | Triggers needs_attention? |
|--------------------|--------------|--------------|---------------------------|
| Unknown            | `-`          | dim gray     | no                        |
| Running            | `Running`    | green        | no                        |
| WaitingForInput    | `INPUT`      | bold yellow  | YES                       |
| PermissionRequired | `PERMISSION` | bold red     | YES                       |
| Stopped            | `Stopped`    | dim          | no                        |

`needs_attention` lights up the row in bold and is the only signal that
should pull the operator's eye to a pane.

## Scenario A — Non-hook agent (bash): Unknown → Stopped only

Goal: confirm a bash shell never spuriously triggers needs_attention.

1. In the dashboard wizard (`N`), pick `Bash Shell (unsandboxed)`, set a
   project dir, and confirm.
2. Verify the new row's status column shows `-` (Unknown, dim gray).
3. Type a few commands in the pane (e.g. `ls`, `echo hi`). Status must
   stay `-` — there are no hooks, so no events transition the state.
4. `exit` the shell to close the pane.
5. The wrapper trap fires `stopped` on EXIT. Status flips to `Stopped`.
6. **Pass criteria**:
   - Row was never bold (needs_attention never triggered).
   - Final status is `Stopped` (without exit code, since the wrapper does
     not currently forward `$?`).

## Scenario B — Claude full lifecycle

Goal: cover all 5 states for `claude` and verify needs_attention semantics.

1. Wizard (`N`) → `Claude Code` → provider e.g. `anthropic` → confirm.
2. Status starts at `-` (Unknown) until the first hook fires.
3. **Expected first hook**: `SessionStart` → mapped via
   `event_map.SessionStart = "running"` → status flips to `Running`.
4. When Claude finishes its first response and idles for input, it emits
   `Notification` with `notification_type = "idle_prompt"`. Hook forwards
   `idle_prompt` → mapped to `input` → status `INPUT` (yellow, bold).
   - **Verify needs_attention triggers here** (row bolded).
5. Submit a tool-using prompt (e.g. "list files"). `PreToolUse` /
   `PostToolUse` → `running`. Status returns to `Running` (no attention).
6. Force a permission prompt — request something requiring approval (e.g.
   write to `/etc`). `Notification.notification_type = "permission_prompt"`
   → `permission` → status `PERMISSION` (red, bold).
   - **Verify needs_attention triggers here** too.
7. Approve in Claude. State returns to `Running`.
8. After the response completes: `idle_prompt` → `INPUT`.
9. Send `/exit` in Claude. The `Stop` hook fires → `stopped` and the
   wrapper EXIT trap also fires. Status `Stopped`. Exit code shown when
   available (e.g. `Stopped (0)`).

**Pass criteria**: every state visited, bold styling appears on INPUT and
PERMISSION only, never on Running/Unknown/Stopped.

## Scenario C — Codex

Goal: validate the `agent-turn-complete` mapping.

1. Wizard (`N`) → `OpenAI Codex` → provider → confirm.
2. Initial status `-` until codex spins up.
3. **No hooks during execution** — codex only fires on turn completion.
   So while codex is thinking the row stays at the last observed state
   (initially `Unknown`). After the first prompt, the visible jump is
   directly to `INPUT` once `agent-turn-complete` arrives.
4. Hook forwards `agent-turn-complete` (or falls back to `turn_complete`
   if `type` is missing). `event_map` maps both to `input` → `INPUT`.
5. Submit another prompt. Status stays at `INPUT` from the dashboard's
   point of view until the next `agent-turn-complete` (codex doesn't
   currently expose a "started thinking" event). To see `Running` you
   need the wrapper to time out and emit it; in practice for codex you
   will mainly observe `-` → `INPUT` → `Stopped`.
6. `/exit` → wrapper trap → `stopped` → status `Stopped`.

**Pass criteria**: `INPUT` after each turn, `Stopped` on close. No
`PERMISSION` (codex does not surface that to us); no spurious bold.

## Scenario D — Pi

Goal: validate session_start / turn_start / tool_call / turn_end /
session_shutdown mappings.

1. Wizard → `Pi` → provider (`anthropic` typically) → confirm.
2. Initial `-`.
3. Pi fires `session_start` immediately → mapped to `input` → `INPUT`.
   needs_attention triggers (Pi sits at the prompt waiting).
4. Submit a prompt requiring a tool call. Sequence: `turn_start`
   (`running`) → one or more `tool_call` (`running`) → `turn_end`
   (`input`).
5. Each transition should be visible (poll interval ~1s; allow up to 2s
   for the dashboard to redraw).
6. `/exit` Pi → `session_shutdown` (`stopped`) plus the wrapper EXIT trap
   (also `stopped`). Status `Stopped`.

**Pass criteria**: all 4 hook events map correctly; bold appears on
`INPUT` segments only.

## Scenario E — OpenCode

1. Wizard → `OpenCode` → provider → confirm. Status `-`.
2. `session.created` (`input`) → status `INPUT` (bold).
3. Submit prompt. `session.status` with sub-state `busy` → `running` →
   `Running`. When it settles, `session.status` with sub-state `idle` →
   `input` → `INPUT` (bold).
4. `session.deleted` (`stopped`) when the agent terminates → `Stopped`.

**Pass criteria**: clean busy ↔ idle oscillation; `stopped` on shutdown.

## Scenario F — Save & restore: Unknown regeneration

Goal: confirm that re-loading state never crashes on legacy rich fields
and that all restored agents come back as `Unknown` until their hooks fire
again.

1. Spawn one agent of each kind (claude, codex, pi). Drive them into
   different states.
2. Quit the dashboard with the save-and-quit shortcut (`s`).
3. Inspect `.lince-dashboard` in the project dir. It should be JSON with
   no `tokens_in` / `tokens_out` / `tool_name` keys (LINCE-119 dropped
   them).
4. (Optional regression test for legacy load) Hand-edit a copy of
   `.lince-dashboard` to inject the legacy keys back:
   ```json
   { "tokens_in": 0, "tokens_out": 0, "tool_name": "Edit" }
   ```
   into one of the agents. Place it back as `.lince-dashboard`.
5. Relaunch the dashboard and choose "Restore" when prompted.
6. **Pass criteria**:
   - No crash on load (serde silently drops the unknown fields).
   - Every restored agent's status column shows `-` (Unknown).
   - As soon as the underlying agent emits its first hook event, status
     transitions normally (the agent processes are *not* restored — only
     the metadata, by design).

## Scenario G — Unknown event handling (negative test)

Goal: confirm an unknown hook event leaves status at Unknown and surfaces a
warning instead of silently coercing to Running.

1. Spawn a Claude agent (so the dashboard accepts events on the
   `claude-status` pipe). Let it settle into `INPUT`.
2. In another terminal inside the same Zellij session, manually pipe a
   bogus event with the same `agent_id`:
   ```bash
   echo '{"agent_id":"agent-1","event":"definitely-not-a-real-event"}' \
       | zellij pipe --name claude-status
   ```
   Replace `agent-1` with the actual ID shown in the dashboard table.
3. **Pass criteria**:
   - The agent's status does **not** flip to Unknown solely from receiving
     the bogus event when its `event_map` has no match — `to_agent_status`
     returns `AgentStatus::Unknown`, but the dashboard's status update
     logic (see `agent.rs`) deliberately suppresses a regression from
     `INPUT` back to `Unknown` on a single bogus event (LINCE-120). Status
     stays at the last known good state (`INPUT`).
   - A warning is logged: check `/tmp/lince-dashboard/dashboard.log` (or
     stderr if running with `RUST_LOG=warn`) for
     `warning: unknown agent event 'definitely-not-a-real-event' from agent-1`.

## Scenario H — Bogus mapping (regression for LINCE-118)

Goal: confirm a misconfigured `event_map` value does not silently coerce.

1. In a scratch config (`~/.config/lince-dashboard/config.toml`), add:
   ```toml
   [agents.claude.event_map]
   PreToolUse = "kinda-running"   # not canonical
   ```
2. Restart the dashboard, spawn Claude, trigger a tool call.
3. **Pass criteria**: status stays at the previous canonical value
   (most likely `Unknown` until SessionStart fires correctly). The
   stderr warning from `to_agent_status` is emitted.
4. Revert the config when done.

## Sign-off checklist

Before approving an m-15 release, all of the following must be green:

- [ ] Build: `cargo build --target wasm32-wasip1` succeeds.
- [ ] Unit tests: `cargo test --target wasm32-wasip1 --no-run` succeeds
      (cannot execute in-plugin due to host imports; native target also
      cannot link — both are expected). Run via cargo separately on the
      pure functions if a wrapper crate is added later.
- [ ] `tests/hook-contract.sh` exits 0.
- [ ] `tests/event-map-coverage.sh` exits 0.
- [ ] Manual scenarios A–H all pass.
