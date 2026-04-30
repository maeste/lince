// lince-pi-hook.ts — Pi extension that emits agent-status events to the
// lince-dashboard via the shared "lince-status" Zellij pipe.
//
// Installed by install-pi-hooks.sh into ~/.pi/agent/extensions/, where Pi
// auto-discovers it on startup. JSON payload schema matches StatusMessage
// in lince-dashboard/plugin/src/types.rs (agent_id, event, tool_name).

import { spawn } from "node:child_process";

export default function (pi: { on: (ev: string, h: (e: any) => void) => void }) {
  const agentId = process.env.LINCE_AGENT_ID;
  const session = process.env.ZELLIJ_SESSION_NAME;
  if (!agentId || !session) return;

  const send = (event: string, extra: Record<string, unknown> = {}) => {
    const payload = JSON.stringify({ agent_id: agentId, event, ...extra });
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

  pi.on("session_start", () => send("running"));
  pi.on("turn_start", () => send("running"));
  pi.on("tool_call", (e) => send("running", { tool_name: e.toolName }));
  pi.on("turn_end", () => send("idle"));
  pi.on("session_shutdown", () => send("stopped"));
}
