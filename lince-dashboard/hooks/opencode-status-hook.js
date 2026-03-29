#!/usr/bin/env node
/**
 * opencode-status-hook.js — OpenCode plugin that reports session lifecycle
 * status to the lince-dashboard Zellij plugin via pipe (primary) and file (fallback).
 *
 * Handles events:
 *   - session.created  → status: idle (waiting for input)
 *   - session.status   → status: running (when busy) or idle (when ready)
 *   - session.idle     → status: idle
 *   - session.deleted  → status: stopped
 *
 * Environment:
 *   LINCE_AGENT_ID   — set by the dashboard when spawning the agent
 *   ZELLIJ           — set by Zellij when running inside a session
 *   LINCE_STATUS_DIR — override for status file directory (default: /tmp/lince-dashboard)
 */

import { execSync } from "child_process";
import { writeFileSync, mkdirSync } from "fs";
import { join } from "path";

const AGENT_ID = process.env.LINCE_AGENT_ID || "";
const STATUS_DIR = process.env.LINCE_STATUS_DIR || "/tmp/lince-dashboard";

function getTimestamp() {
    try {
        return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    } catch {
        return "";
    }
}

function buildPayload(event, extra = {}) {
    const base = {
        agent_id: AGENT_ID,
        event,
        timestamp: getTimestamp(),
        ...extra,
    };
    return JSON.stringify(base);
}

function sendViaZellijPipe(payload) {
    if (!process.env.ZELLIJ) {
        return false;
    }
    try {
        execSync(
            `echo '${payload.replace(/'/g, "'\\''")}' | timeout 2 zellij pipe --name "lince-status"`,
            { timeout: 3000, encoding: "utf8" }
        );
        return true;
    } catch {
        return false;
    }
}

function writeStatusFile(status) {
    try {
        mkdirSync(STATUS_DIR, { recursive: true });
        writeFileSync(join(STATUS_DIR, `${AGENT_ID}.state`), status);
    } catch {
        // ignore
    }
}

function reportStatus(status, extra = {}) {
    if (!AGENT_ID) return;
    sendViaZellijPipe(buildPayload(status, extra));
    writeStatusFile(status);
}

function getModelFromEvent(event) {
    return event.properties?.model || event.properties?.provider || null;
}

function getToolFromEvent(event) {
    return event.properties?.toolName || event.properties?.tool || null;
}

export default async ({ directory }) => {
    return {
        event: async ({ event }) => {
            const extra = {};
            const model = getModelFromEvent(event);
            const tool = getToolFromEvent(event);
            if (model) extra.model = model;
            if (tool) extra.tool_name = tool;

            switch (event.type) {
                case "session.created":
                    reportStatus("idle", extra);
                    break;

                case "session.status":
                    try {
                        const statusType = event.properties?.status?.type;
                        reportStatus(statusType === "busy" ? "running" : "idle", extra);
                    } catch {
                        reportStatus("idle", extra);
                    }
                    break;

                case "session.idle":
                    reportStatus("idle", extra);
                    break;

                case "session.deleted":
                    reportStatus("stopped", extra);
                    break;
            }
        },
    };
};
