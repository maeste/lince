# Experimental Features — Validation Guide

All features below are marked **experimental**. They need manual testing before being considered stable. If you can help validate any of these, please see [CONTRIBUTING.md](../CONTRIBUTING.md).

Each section is a standalone test you can run independently. Check the boxes as you validate.

---

## 1. Credential Proxy Isolation

**What it does**: A localhost HTTP proxy intercepts API calls and injects credentials on the host side. API keys never enter the sandbox.

**Prerequisites**: A working `agent-sandbox` installation with at least one API key configured in a profile.

### Test 1.1: Proxy starts and stops correctly

```bash
# 1. Enable the proxy in config
#    Edit ~/.agent-sandbox/config.toml:
#    [security]
#    credential_proxy = true

# 2. Configure a profile with an API key
#    [claude.profiles.test]
#    description = "Test profile"
#    [claude.profiles.test.env]
#    ANTHROPIC_API_KEY = "sk-ant-test-key-here"

# 3. Run with dry-run to see the proxy would start
agent-sandbox run -P test --dry-run

# 4. Check proxy status (should say "not running" since dry-run doesn't start it)
agent-sandbox proxy-status
```

- [ ] `--dry-run` output mentions credential proxy configuration
- [ ] `proxy-status` shows "not running" when no sandbox is active

### Test 1.2: Proxy injects credentials

```bash
# 1. Start a sandbox run (will start proxy in background)
agent-sandbox run -P test

# 2. In another terminal, check proxy is running
agent-sandbox proxy-status
```

- [ ] `proxy-status` shows port, PID, and configured domains
- [ ] The sandbox banner shows credential proxy info (port, domains)
- [ ] API keys (ANTHROPIC_API_KEY, etc.) are NOT in the sandbox environment (check with `env | grep API` inside sandbox)
- [ ] The agent can still make API calls successfully (requests go through proxy)

### Test 1.3: Proxy stops on sandbox exit

```bash
# 1. Exit the sandbox (Ctrl+C or agent exits)
# 2. Check proxy status
agent-sandbox proxy-status
```

- [ ] Proxy is no longer running after sandbox exits
- [ ] PID file is cleaned up

### Test 1.4: Cloud metadata endpoints are blocked

```bash
# Inside the sandbox with proxy enabled:
curl -s http://169.254.169.254/latest/meta-data/ 2>&1
# Should fail or return 403
```

- [ ] Requests to `169.254.169.254` are blocked
- [ ] Requests to `metadata.google.internal` are blocked

### Test 1.5: Backward compatibility (proxy disabled)

```bash
# Ensure credential_proxy = false (default)
agent-sandbox run
```

- [ ] Agent works normally without proxy
- [ ] API keys are in the sandbox environment as before
- [ ] No proxy PID file created

---

## 2. Filesystem Snapshots and Rollback

**What it does**: Creates rsync-based hardlink snapshots of the project directory and agent config directory. Supports interactive restore.

**Prerequisites**: A working `agent-sandbox` installation, `rsync` installed.

### Test 2.1: Manual snapshot creation

```bash
cd ~/project/some-repo

# Create a snapshot
agent-sandbox snapshot

# Verify it exists
agent-sandbox snapshot-list
```

- [ ] Snapshot is created for both project and config
- [ ] `snapshot-list` shows the snapshot with timestamp and size
- [ ] Snapshot dir exists at `~/.agent-sandbox/snapshots/`

### Test 2.2: Config-only and project-only

```bash
agent-sandbox snapshot --config-only
agent-sandbox snapshot --project-only
agent-sandbox snapshot-list
```

- [ ] `--config-only` creates only a config snapshot
- [ ] `--project-only` creates only a project snapshot
- [ ] `snapshot-list` shows them separately

### Test 2.3: Snapshot diff

```bash
# 1. Create a snapshot
agent-sandbox snapshot

# 2. Modify a file in the project
echo "test change" >> some-file.txt

# 3. Diff against snapshot
agent-sandbox snapshot-diff
```

- [ ] Diff shows `some-file.txt` as modified
- [ ] Diff output shows the actual content change

### Test 2.4: Cross-session diff (two timestamps)

```bash
# 1. Create first snapshot
agent-sandbox snapshot
# Note timestamp from snapshot-list

# 2. Make a change
echo "change 1" >> file1.txt

# 3. Create second snapshot
agent-sandbox snapshot

# 4. Compare the two
agent-sandbox snapshot-diff <ts1> <ts2>
```

- [ ] Shows changes between the two snapshots
- [ ] Does not compare against current state

### Test 2.5: Interactive restore

```bash
# 1. Create snapshot, modify file, then restore
agent-sandbox snapshot
echo "unwanted change" > important-file.txt
agent-sandbox snapshot-restore

# 2. For each changed file, accept or reject
```

- [ ] Interactive prompt appears for each changed file
- [ ] Accepting restores the file from snapshot
- [ ] Rejecting keeps the current version
- [ ] Restored file matches the snapshot content

### Test 2.6: Auto-snapshot (config)

```bash
# Ensure auto_config = true in config.toml (default)
agent-sandbox run
# Exit immediately

agent-sandbox snapshot-list --config
```

- [ ] A config snapshot was created automatically before the run
- [ ] No snapshot created if `auto_config = false`

### Test 2.7: Auto-snapshot (project, opt-in)

```bash
# Set auto_project = true in config.toml
agent-sandbox run
# Exit immediately

agent-sandbox snapshot-list --project
```

- [ ] A project snapshot was created automatically
- [ ] Large dirs (.git, node_modules) are excluded

### Test 2.8: Snapshot pruning

```bash
# Create more snapshots than max_config_snapshots (default 5)
for i in $(seq 1 7); do agent-sandbox snapshot --config-only; sleep 1; done

agent-sandbox snapshot-list --config
```

- [ ] Only `max_config_snapshots` snapshots remain (oldest pruned)

### Test 2.9: diff/merge regression

```bash
# Verify existing diff/merge still works exactly as before
agent-sandbox diff
agent-sandbox merge
```

- [ ] `diff` shows same output as before the changes
- [ ] `merge` interactive UX works identically

---

## 3. Learn Mode

**What it does**: Runs the agent under `strace` to discover filesystem, network, and executable access patterns. Generates config suggestions.

**Prerequisites**: `strace` installed, a working `agent-sandbox` installation.

### Test 3.1: Basic learn session

```bash
cd ~/project/some-repo

# Run learn for 30 seconds
agent-sandbox learn --duration 30
```

- [ ] strace is launched and attaches to the sandbox
- [ ] Agent runs inside a permissive sandbox
- [ ] After timeout, a report is printed
- [ ] Report shows filesystem access categories (project, home_config, system, toolchain)
- [ ] Report shows network connections with hostnames
- [ ] Report shows executed binaries
- [ ] TOML suggestion fragment is saved to temp file

### Test 3.2: Learn with specific agent

```bash
agent-sandbox learn -a codex --duration 30
```

- [ ] Codex (or configured agent) runs instead of Claude
- [ ] Report reflects that agent's access patterns

### Test 3.3: Compare mode

```bash
agent-sandbox learn --compare --duration 30
```

- [ ] Report shows over-permissive areas (allowed but not accessed)
- [ ] Report shows under-permissive areas (accessed but not allowed)

### Test 3.4: Apply suggestions

```bash
agent-sandbox learn --apply --duration 30

# Check config
cat ~/.agent-sandbox/config.toml
```

- [ ] Suggestions are appended to config.toml
- [ ] Existing config is not corrupted
- [ ] Re-running `--apply` replaces previous suggestions (not duplicated)

### Test 3.5: Output to file

```bash
agent-sandbox learn --output /tmp/learn-report.toml --duration 30
cat /tmp/learn-report.toml
```

- [ ] TOML fragment is written to the specified file
- [ ] File contains valid TOML

### Test 3.6: strace missing

```bash
# Temporarily hide strace
PATH_BAK="$PATH"
export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v strace | tr '\n' ':')
agent-sandbox learn 2>&1
export PATH="$PATH_BAK"
```

- [ ] Clear error message about strace not being found
- [ ] Suggests installation command

---

## 4. nono Backend Support (sandbox)

**What it does**: Allows using nono as an alternative sandbox backend. Generates nono profiles from lince config.

**Prerequisites**: `nono` installed (`cargo install nono-cli` or `brew install nono`).

### Test 4.1: Backend detection

```bash
agent-sandbox status
```

- [ ] Shows detected backends (agent-sandbox: yes/no, nono: yes/no)
- [ ] Shows active backend based on config

### Test 4.2: nono-sync dry-run

```bash
agent-sandbox nono-sync --dry-run
```

- [ ] Prints JSON profile for each configured agent
- [ ] Profile uses `lince-` prefix
- [ ] Warnings for untranslatable features (bwrap_conflict, etc.)
- [ ] No files written

### Test 4.3: nono-sync write

```bash
agent-sandbox nono-sync
ls ~/.config/nono/profiles/lince-*.json
```

- [ ] JSON files created at `~/.config/nono/profiles/lince-<agent>.json`
- [ ] One file per configured agent
- [ ] Files contain valid JSON

### Test 4.4: nono-sync specific agent

```bash
agent-sandbox nono-sync --agent claude --dry-run
```

- [ ] Only generates profile for claude
- [ ] Other agents are skipped

### Test 4.5: Run with nono backend

```bash
# Set backend = "nono" in config.toml
agent-sandbox run
```

- [ ] Runs `nono run --profile lince-claude -- claude ...` instead of bwrap
- [ ] Agent starts successfully inside nono sandbox
- [ ] Sandbox banner shows nono backend

### Test 4.6: Auto backend selection

```bash
# Set backend = "auto" in config.toml
agent-sandbox status
```

- [ ] On Linux with bwrap: selects agent-sandbox
- [ ] On Linux without bwrap but with nono: selects nono
- [ ] On macOS: selects nono (or error if missing)

### Test 4.7: macOS error message (Linux simulation)

```bash
# Can't easily test on Linux, but verify the code path:
# Temporarily rename bwrap and nono, set backend = "agent-sandbox"
agent-sandbox run 2>&1
```

- [ ] Clear error when configured backend is not available
- [ ] Suggests installing the missing backend

---

## 5. nono Backend Support (dashboard)

**What it does**: The lince-dashboard can launch agents via nono instead of agent-sandbox.

**Prerequisites**: lince-dashboard installed, `nono` installed, nono profiles generated (`agent-sandbox nono-sync`).

### Test 5.1: Backend auto-detection

```bash
# Launch dashboard
zd

# Check that backend detection runs (visible in agent detail panel)
```

- [ ] Dashboard starts without errors
- [ ] Backend detection completes (no "unknown backend" warnings)

### Test 5.2: Agent type shows backend

```bash
# In dashboard, spawn an agent (n or N)
# Select the agent, press Enter for detail panel
```

- [ ] Detail panel shows sandbox backend (e.g., "[bwrap]" or "[nono]")
- [ ] Table shows backend indicator

### Test 5.3: Per-agent backend override

```toml
# In ~/.config/lince-dashboard/config.toml or agents-defaults.toml:
[agents.claude]
sandbox_backend = "nono"
```

```bash
# Spawn a claude agent in the dashboard
```

- [ ] Claude agent uses nono backend
- [ ] Other agents still use default backend

### Test 5.4: Dashboard config sandbox_backend

```toml
# In config.toml:
[dashboard]
sandbox_backend = "nono"
```

- [ ] All sandboxed agents default to nono
- [ ] Per-agent overrides still work

### Test 5.5: Regression — agent-sandbox backend

```bash
# Ensure sandbox_backend = "auto" or "agent-sandbox"
# Spawn agents normally
```

- [ ] All existing functionality works as before
- [ ] No regressions in agent launching, status reporting, or pane management

---

## 6. Install Script Updates

### Test 6.1: sandbox/install.sh on Linux with bwrap

```bash
cd sandbox && ./install.sh
```

- [ ] Detects bwrap, installs normally
- [ ] Step 5 shows nono status (not installed or detected)
- [ ] Summary shows backend info

### Test 6.2: sandbox/install.sh on Linux with nono

```bash
# Install nono first, then:
cd sandbox && ./install.sh
```

- [ ] Detects both bwrap and nono
- [ ] Runs nono-sync to generate profiles
- [ ] Summary shows "auto (agent-sandbox + nono)"

### Test 6.3: sandbox/update.sh with nono

```bash
cd sandbox && ./update.sh
```

- [ ] Step 3 re-runs nono-sync if nono is detected
- [ ] Profiles are updated

### Test 6.4: sandbox/uninstall.sh with nono profiles

```bash
cd sandbox && ./uninstall.sh
```

- [ ] Offers to remove `lince-*.json` nono profiles
- [ ] Does NOT attempt to uninstall nono itself
- [ ] Existing uninstall flow (command, config dir) unchanged

### Test 6.5: lince-dashboard/install.sh sandbox check

```bash
cd lince-dashboard && ./install.sh
```

- [ ] Post-install shows detected sandbox backends
- [ ] On macOS (or without bwrap): guides to install nono

---

## Reporting Results

When you've completed testing, please:

1. Check the boxes above for passing tests
2. File issues for any failures at the project's issue tracker
3. Note your environment: OS, kernel version, Python version, nono version (if applicable)

See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to submit your results.
