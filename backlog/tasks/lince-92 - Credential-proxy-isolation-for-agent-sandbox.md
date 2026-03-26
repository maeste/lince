---
id: LINCE-92
title: Credential proxy isolation for agent-sandbox
status: Done
assignee: []
created_date: '2026-03-26 12:29'
updated_date: '2026-03-26 13:35'
labels:
  - sandbox
  - security
  - feature
milestone: m-13
dependencies: []
references:
  - sandbox/docs/comparison-agent-sandbox-vs-nono.md
  - 'https://github.com/always-further/nono (crates/nono-proxy/)'
  - sandbox/agent-sandbox
  - sandbox/agents-defaults.toml
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Currently, API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.) must exist inside the sandbox process memory because the agent needs them to call its provider's API. A compromised or prompt-injected agent could exfiltrate these secrets via network requests to arbitrary endpoints.

nono solves this with a localhost HTTP proxy that intercepts outbound API requests and injects credentials into headers — the secret never enters the sandbox at all.

## Implementation Plan

### Phase 1: Proxy Design
1. Design a lightweight HTTP CONNECT proxy in Python (stdlib only — `http.server` + `socketserver` or `asyncio`). The proxy runs **outside** the sandbox on the host.
2. The proxy reads credentials from the agent's profile config (`[agents.<name>.profiles.<profile>]`) and maps them to injection rules:
   - Header injection: `Authorization: Bearer $KEY` for API calls
   - Support patterns: Anthropic (`x-api-key`), OpenAI (`Authorization: Bearer`), Google (`Authorization: Bearer` from ADC), custom header mappings
3. The proxy listens on a Unix domain socket (preferred, simpler security) or `127.0.0.1:<random_port>`.

### Phase 2: Sandbox Integration
1. Inside the sandbox, set `HTTP_PROXY` / `HTTPS_PROXY` env vars pointing to the proxy.
2. Remove API key env vars from the sandbox environment (they no longer need to pass through `--clearenv` whitelist).
3. The proxy socket/port is bind-mounted read-only into the sandbox.
4. Add a config toggle: `[security] credential_proxy = true|false` (default false for backward compat).

### Phase 3: Allowlist and Filtering
1. The proxy maintains a domain allowlist per agent profile (e.g., `api.anthropic.com`, `api.openai.com`, `generativelanguage.googleapis.com`).
2. Requests to non-allowlisted domains pass through WITHOUT credential injection (agents still need general internet for package managers, git clone, etc.).
3. Block cloud metadata endpoints: `169.254.169.254`, `metadata.google.internal`, `metadata.azure.internal` (SSRF protection).

### Phase 4: Config & UX
1. Extend `agents-defaults.toml` with per-agent credential proxy rules (which headers, which domains).
2. Add `agent-sandbox proxy-status` command to check proxy health.
3. Document the feature in README.md.

## Key Design Decisions
- **Python stdlib only** — no external dependencies, consistent with project philosophy.
- **Opt-in** — existing setups continue to work; proxy mode is a config flag.
- **Unix socket preferred** — avoids port conflicts, simpler auth (socket file permissions).
- **Domain allowlist, not blocklist** — fail-secure for credential injection; general traffic still passes.
- **Proxy runs on host** — it's a sibling process to bwrap, not inside the sandbox.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.) are NOT present inside the sandbox environment when credential_proxy=true
- [ ] #2 Proxy correctly injects credentials into outbound API requests matching configured domains
- [ ] #3 Requests to non-allowlisted domains pass through without credential injection
- [ ] #4 Cloud metadata endpoints (169.254.169.254, metadata.google.internal, metadata.azure.internal) are blocked
- [ ] #5 All existing agents (Claude, Codex, Gemini, Aider, OpenCode, Amp) work with proxy mode enabled
- [ ] #6 Proxy uses zero external Python dependencies
- [ ] #7 Config toggle allows disabling proxy mode (backward compatible)
- [ ] #8 agent-sandbox proxy-status command reports proxy health
- [ ] #9 Proxy auto-starts and auto-stops with sandbox lifecycle
- [ ] #10 Unit tests cover: credential injection, domain filtering, metadata blocking, lifecycle management
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented in sandbox/agent-sandbox:

- `CredentialProxy` class (line 474): ThreadingTCPServer-based HTTP proxy with CONNECT tunneling and reverse proxy credential injection
- `_ProxyRequestHandler` (line 270): Handles API forwarding with header injection, CONNECT tunneling for general traffic, and metadata endpoint blocking
- `_collect_proxy_rules()` (line 581): Auto-maps known env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, GEMINI_API_KEY) to API domains and headers
- `cmd_proxy_status()` (line 1675): Shows proxy status from PID file
- Integration in `cmd_run()`: starts proxy, rewrites BASE_URL env vars, strips API keys from sandbox env, cleans up on exit
- Config: `[security] credential_proxy = false` (opt-in), `[credential_proxy] blocked_hosts` for extra blocking
- Updated config.toml.example and agents-defaults.toml with credential proxy documentation
<!-- SECTION:NOTES:END -->
