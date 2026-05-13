# Hook Script Templates

Skeleton hook scripts for Tier A agent registration. Pick the language that
matches the agent's hook system (most agents support bash via a generic
"run external program" hook; some require TypeScript / JavaScript).

Every template:

- Reads `$LINCE_AGENT_ID` and exits 0 silently if empty
- Emits the m-15 minimal JSON contract `{"agent_id":"<id>","event":"<name>"}`
- Sends to the Zellij pipe `$LINCE_PIPE` (default `lince-status`)
- Always writes a file fallback to `/tmp/lince-dashboard/<id>.state`
- Never blocks — Zellij calls are wrapped in `|| true`

The hook emits the agent's **native** event name verbatim. Translation to a
canonical state (`running` / `input` / `permission` / `stopped`) happens in
the dashboard via `[agents.<key>.event_map]`, NOT inside the hook.

---

## bash

Target: `~/.local/share/lince/hooks/<key>-status-hook.sh`. After writing,
`chmod +x` it.

```bash
#!/usr/bin/env bash
set -uo pipefail

AGENT_ID="${LINCE_AGENT_ID:-}"
[[ -z "$AGENT_ID" ]] && exit 0

PIPE_NAME="${LINCE_PIPE:-lince-status}"

send() {
    local event="$1"
    local payload
    payload=$(printf '{"agent_id":"%s","event":"%s"}' "$AGENT_ID" "$event")

    # Primary: Zellij pipe (only when running inside Zellij)
    if command -v zellij >/dev/null 2>&1 && [[ -n "${ZELLIJ:-}" ]]; then
        echo "$payload" | timeout 2 zellij pipe --name "$PIPE_NAME" 2>/dev/null || true
    fi

    # Fallback: file watcher
    mkdir -p /tmp/lince-dashboard
    echo "$payload" > "/tmp/lince-dashboard/${AGENT_ID}.state"
}

# ---------------------------------------------------------------------------
# TODO: customise the trigger logic for your agent.
#
# Common patterns:
#   - The agent invokes this script with the event name as $1:
#         send "$1"
#   - The agent pipes a JSON payload to stdin:
#         event=$(jq -r '.type // "unknown"' <&0)
#         send "$event"
#   - The hook is wired into multiple lifecycle phases (script per phase):
#         send "PreToolUse"       # or "Stop", "idle_prompt", ...
#
# Replace the line below with the right call for your agent.
# ---------------------------------------------------------------------------

send "${1:-unknown}"
```

---

## TypeScript / JavaScript

Target: `~/.local/share/lince/hooks/<key>-status-hook.{ts,js}`. For TS, the
agent must run it through a TS runtime (`tsx`, `bun`, `deno`); for plain JS,
Node 18+ works directly.

```typescript
#!/usr/bin/env node
// or: #!/usr/bin/env bun

import { execSync } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";

const AGENT_ID = process.env.LINCE_AGENT_ID;
if (!AGENT_ID) process.exit(0);

const PIPE_NAME = process.env.LINCE_PIPE ?? "lince-status";

function send(event: string): void {
    const payload = JSON.stringify({ agent_id: AGENT_ID, event });

    // Primary: Zellij pipe
    if (process.env.ZELLIJ) {
        try {
            execSync(`zellij pipe --name ${PIPE_NAME}`, {
                input: payload,
                timeout: 2000,
                stdio: ["pipe", "ignore", "ignore"],
            });
        } catch { /* never block */ }
    }

    // Fallback: file watcher
    try {
        mkdirSync("/tmp/lince-dashboard", { recursive: true });
        writeFileSync(`/tmp/lince-dashboard/${AGENT_ID}.state`, payload);
    } catch { /* never block */ }
}

// ---------------------------------------------------------------------------
// TODO: customise the trigger logic for your agent.
//
// If the agent passes JSON on stdin:
//   const raw = require("node:fs").readFileSync(0, "utf8");
//   const data = JSON.parse(raw);
//   send(data.type ?? "unknown");
//
// If the agent passes the event as argv:
//   send(process.argv[2] ?? "unknown");
// ---------------------------------------------------------------------------

send(process.argv[2] ?? "unknown");
```

---

## Test the wiring

After writing the hook, verify the pipe is reachable from inside Zellij:

```bash
echo '{"agent_id":"test","event":"running"}' | zellij pipe --name lince-status
```

If the dashboard pane shows the `test` agent transitioning to `Running`, the
plumbing is correct. From there, the only remaining work is making your hook
produce the right native event names for your agent's lifecycle.
