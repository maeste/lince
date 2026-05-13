// lince-pi-hook.ts — Pi extension that emits agent-status events to the
// lince-dashboard via the shared "lince-status" Zellij pipe.
//
// Installed by install-pi-hooks.sh into ~/.pi/agent/extensions/, where Pi
// auto-discovers it on startup. JSON payload schema is the minimal contract
// shared by all hook scripts: {agent_id, event}. Native event names are
// forwarded verbatim — the dashboard's per-agent event_map (in
// agents-defaults.toml) maps them to canonical status values. See
// LINCE-118 / LINCE-122.

import { spawn } from "node:child_process";

export default function (pi: { on: (ev: string, h: (e: any) => void) => void }) {
  const agentId = process.env.LINCE_AGENT_ID;
  const session = process.env.ZELLIJ_SESSION_NAME;
  if (!agentId || !session) return;

  const send = (event: string) => {
    const payload = JSON.stringify({ agent_id: agentId, event });
    try {
      const child = spawn(
        "zellij",
        ["--session", session, "pipe", "--name", "lince-status"],
        { stdio: ["pipe", "ignore", "ignore"] },
      );
      child.on("error", () => {});
      child.stdin.end(payload);
    } catch {}
  };

  pi.on("session_start", () => send("session_start"));
  pi.on("turn_start", () => send("turn_start"));
  pi.on("tool_call", () => send("tool_call"));
  pi.on("turn_end", () => send("turn_end"));
  pi.on("session_shutdown", () => send("session_shutdown"));
}
