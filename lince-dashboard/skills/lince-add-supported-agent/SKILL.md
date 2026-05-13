---
name: lince-setup
description: Register a new AI coding agent with the lince-dashboard and agent-sandbox. The agent provides its own requirements (binary, config dirs, API keys, sandbox behavior) and this skill generates correct TOML configuration. Use when adding a new agent type, setting up multi-agent support, or when asked to add agent, register agent, setup agent, configure agent for dashboard.
license: MIT
compatibility: Requires lince-dashboard and agent-sandbox installed. Works with any agent supporting agentskills.io.
metadata:
  author: lince
  version: "1.0"
---

# lince-setup: Agent Self-Registration Skill

Register a new AI coding agent with the lince ecosystem (agent-sandbox + lince-dashboard).

This skill walks you through self-identifying your capabilities, then generates and writes
the correct TOML configuration so the dashboard can manage you and the sandbox can run you.

## References

- `references/config-schema.md` -- Full field reference for all config options
- `references/examples.md` -- Real agent configuration examples
- `scripts/validate-agent.sh` -- Post-registration validation script

---

## Step 1: Self-Identify

You are the agent being registered. Answer the following questions about YOURSELF.
These are introspection questions -- describe your own binary, config, and runtime needs.

Provide the following information:

1. **Binary / command name**: What is the executable command to run you?
   - Example: `codex`, `gemini`, `opencode`, `kiro`, `aider`

2. **Config directory**: Where is your configuration stored on disk?
   - Example: `~/.codex/`, `~/.config/opencode/`, `~/.gemini/`
   - This directory will be bind-mounted read-only into the sandbox.

3. **API key environment variables**: What env vars do you need for authentication?
   - Example: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
   - These will be passed through to the sandbox from the host environment.

4. **Default CLI arguments**: What args should be used for autonomous/headless mode?
   - Example: `["--full-auto"]`, `["--yes"]`, `[]`
   - These are appended to every invocation by the sandbox.

5. **Internal sandbox conflict**: Do you use bwrap, Docker, or any internal sandbox?
   - If yes: what CLI flag disables your internal sandbox?
   - Example: Codex uses bwrap internally, disabled with `--no-sandbox`
   - Example: Gemini uses Docker sandbox, disabled with `--sandbox none`
   - If no internal sandbox: `bwrap_conflict = false`

Report all five answers before proceeding.

---

## Step 2: Derive Config Key

Convert your binary name into a config key:
- Lowercase the name
- Replace spaces and underscores with hyphens
- Remove any special characters

Examples: `codex` -> `codex`, `open_code` -> `open-code`, `My Agent` -> `my-agent`

Present the derived key to the user and ask for confirmation before continuing.

---

## Step 3: Check Existing Config

Before writing anything, check whether `[agents.<key>]` already exists in the sandbox config.

Read `~/.agent-sandbox/config.toml` and search for a section matching your derived key.

- If the section **already exists**: inform the user and offer to **update** it rather than
  creating a duplicate. Show the existing config block.
- If the section **does not exist**: proceed to generation.

Also check the dashboard config. The dashboard agents-defaults file is at
`~/.agent-sandbox/agents-defaults.toml` (for the dashboard). Check for an existing
`[<key>]` section there as well.

---

## Step 4: Generate Sandbox TOML

Using the information from Step 1, generate an `[agents.<key>]` block for
`~/.agent-sandbox/config.toml`:

```toml
[agents.<key>]
command = "<binary>"
default_args = [<args as quoted strings>]
env = { <API_KEY> = "$<API_KEY>" }
home_ro_dirs = ["<config_dir_relative_to_home>"]
home_rw_dirs = []
bwrap_conflict = <true|false>
disable_inner_sandbox_args = [<args if bwrap_conflict is true>]
```

Notes on field values:
- `home_ro_dirs` paths are relative to `~` (e.g. `.codex` not `~/.codex/`)
- `env` uses `$VAR` syntax for environment variable expansion at runtime
- `disable_inner_sandbox_args` is only needed when `bwrap_conflict = true`
- See `references/config-schema.md` for the full field reference

---

## Step 5: Generate Dashboard TOML

Generate a dashboard agent type block. This goes in `~/.agent-sandbox/agents-defaults.toml`
as a top-level `[<key>]` section (not under `[agents.]`):

```toml
[<key>]
command = ["agent-sandbox", "run", "-a", "<key>", "-p", "{project_dir}"]
display_name = "<Agent Display Name>"
short_label = "<3CH>"
color = "<color>"
sandboxed = true
has_native_hooks = false
pane_title_pattern = "<binary>"
status_pipe_name = "lince-status"
```

Apply these defaults (the skill knows the lince conventions):

| Field | Default Value | Rationale |
|-------|---------------|-----------|
| `has_native_hooks` | `false` | Only Claude Code has native status hooks |
| `status_pipe_name` | `"lince-status"` | Standard pipe for non-Claude agents via lince-agent-wrapper |
| `sandboxed` | `true` | Lince convention: all agents run sandboxed |
| `pane_title_pattern` | binary name | Used by dashboard to detect agent panes |
| `color` | suggest based on name | Pick from: red, green, yellow, blue, magenta, cyan, white |
| `short_label` | first 3 chars, uppercase | 3-character label for table column |

If the agent needs API key env vars, add an `[<key>.env_vars]` sub-table:

```toml
[<key>.env_vars]
<API_KEY> = "$<API_KEY>"
```

If there is a bwrap conflict, include:

```toml
bwrap_conflict = true
disable_inner_sandbox_args = [<args>]
```

If the agent needs config dirs mounted read-only:

```toml
home_ro_dirs = ["~/.config_dir/"]
```

---

## Step 6: Write Config

Present BOTH generated TOML blocks to the user in a single summary:

```
=== Sandbox Config (appended to ~/.agent-sandbox/config.toml) ===
<sandbox TOML block>

=== Dashboard Config (appended to ~/.agent-sandbox/agents-defaults.toml) ===
<dashboard TOML block>
```

Ask the user to confirm before writing. Upon confirmation:

1. **Sandbox config**: Append the sandbox TOML block to `~/.agent-sandbox/config.toml`
   - Use `cat >> ~/.agent-sandbox/config.toml` or equivalent append operation
   - Add a blank line before the new block for readability
   - Do NOT overwrite the existing file

2. **Dashboard config**: Append the dashboard TOML block to `~/.agent-sandbox/agents-defaults.toml`
   - Use `cat >> ~/.agent-sandbox/agents-defaults.toml` or equivalent append operation
   - Add a blank line before the new block for readability
   - Do NOT overwrite the existing file

This skill must be **idempotent**: if a section already exists (detected in Step 3),
update it in place rather than appending a duplicate.

---

## Step 7: Validate

After writing, run the validation script to verify correctness:

```bash
bash <skill_dir>/scripts/validate-agent.sh <key>
```

Or run the dry-run command directly:

```bash
agent-sandbox run -a <key> -p /tmp/test --dry-run
```

Check the output for errors. If the dry run succeeds, registration is complete.
If it fails, review the error message, fix the config, and re-run validation.

---

## Important Notes

- This skill is idempotent. Running it again for the same agent detects existing
  config and offers to update rather than duplicate.
- The `has_native_hooks` field should be `false` for all agents except Claude Code.
  Agents without native hooks use lince-agent-wrapper for status reporting.
- The `status_pipe_name` for non-Claude agents is always `lince-status`.
  Claude Code uses `claude-status` (reserved).
- Colors must be valid ANSI color names: red, green, yellow, blue, magenta, cyan, white.
- The `{project_dir}` placeholder in the dashboard command template is replaced at
  runtime with the actual project directory path.
- See `references/config-schema.md` for complete field documentation.
- See `references/examples.md` for real-world agent configuration examples.
