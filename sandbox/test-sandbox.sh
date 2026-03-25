#!/usr/bin/env bash
# test-sandbox.sh — Verify agent-sandbox restrictions from INSIDE the sandbox.
#
# Usage:
#   agent-sandbox run -- bash /path/to/test-sandbox.sh
#
# The script exercises every isolation boundary and prints a pass/fail report.
# Exit code 0 = all critical tests passed, 1 = at least one critical failure.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS=0
FAIL=0
WARN=0
CRITICAL_FAIL=0

pass() { ((PASS++)); printf '  \033[32m✓ PASS\033[0m  %s\n' "$1"; }
fail() { ((FAIL++)); printf '  \033[31m✗ FAIL\033[0m  %s\n' "$1"; }
critical_fail() { ((CRITICAL_FAIL++)); ((FAIL++)); printf '  \033[31;1m✗ CRITICAL FAIL\033[0m  %s\n' "$1"; }
warn() { ((WARN++)); printf '  \033[33m⚠ WARN\033[0m  %s\n' "$1"; }
header() { printf '\n\033[1;36m── %s ──\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
# 1. Filesystem write isolation
# ---------------------------------------------------------------------------
header "Filesystem Write Isolation"

# Home directory should be a tmpfs — writes succeed locally but must not
# persist on the host.  We test that we CANNOT write to well-known host paths.

ESCAPE_FILE="$HOME/.sandbox-escape-test-$$"
if touch "$ESCAPE_FILE" 2>/dev/null; then
    # Writing to $HOME succeeds (it's a tmpfs), that's expected inside bwrap.
    # The real test is that this file does NOT appear on the host.
    # We can't verify that from in here, so we check the mount type.
    mount_info=$(mount 2>/dev/null | grep " $HOME " || true)
    if echo "$mount_info" | grep -q tmpfs; then
        pass "Home is tmpfs — writes are ephemeral"
    else
        warn "Home is writable but could not confirm tmpfs mount (verify on host that $ESCAPE_FILE is absent)"
    fi
    rm -f "$ESCAPE_FILE"
else
    pass "Home is not writable at all"
fi

# Write outside project — should fail
if touch /etc/.sandbox-test-$$ 2>/dev/null; then
    rm -f /etc/.sandbox-test-$$
    critical_fail "Write to /etc succeeded — sandbox is NOT enforcing read-only root"
else
    pass "Cannot write to /etc"
fi

if touch /usr/.sandbox-test-$$ 2>/dev/null; then
    rm -f /usr/.sandbox-test-$$
    critical_fail "Write to /usr succeeded"
else
    pass "Cannot write to /usr"
fi

if touch /var/.sandbox-test-$$ 2>/dev/null; then
    rm -f /var/.sandbox-test-$$
    critical_fail "Write to /var succeeded"
else
    pass "Cannot write to /var"
fi

# Project dir should be writable
PROJECT_TEST="./.sandbox-write-test-$$"
if touch "$PROJECT_TEST" 2>/dev/null; then
    rm -f "$PROJECT_TEST"
    pass "Project directory is writable"
else
    fail "Project directory is NOT writable (expected read-write)"
fi

# ---------------------------------------------------------------------------
# 2. Read-only directories
# ---------------------------------------------------------------------------
header "Read-Only Directory Enforcement"

# ~/project is typically ro-bound; try writing to a sibling project
RO_CANDIDATES=("$HOME/project" "$HOME/.local" "$HOME/.config")
for d in "${RO_CANDIDATES[@]}"; do
    if [ -d "$d" ]; then
        if touch "$d/.sandbox-ro-test-$$" 2>/dev/null; then
            rm -f "$d/.sandbox-ro-test-$$"
            fail "$d is writable (expected read-only)"
        else
            pass "$d is read-only"
        fi
    fi
done

# ---------------------------------------------------------------------------
# 3. Sensitive files hidden
# ---------------------------------------------------------------------------
header "Sensitive Files Hidden"

check_hidden() {
    local path="$1" label="$2"
    if [ -e "$path" ]; then
        fail "$label exists at $path"
    else
        pass "$label is hidden"
    fi
}

check_hidden "$HOME/.ssh"          "SSH keys directory"
check_hidden "$HOME/.aws"          "AWS credentials"
check_hidden "$HOME/.gnupg"        "GPG keyring"
check_hidden "$HOME/.bash_history" "Bash history"
check_hidden "$HOME/.bashrc"       "Bash RC"
check_hidden "$HOME/.zshrc"        "Zsh RC"
check_hidden "$HOME/.netrc"        ".netrc"
check_hidden "$HOME/.npmrc"        ".npmrc (may contain tokens)"
check_hidden "$HOME/.docker"       "Docker config"
check_hidden "$HOME/.kube"         "Kubernetes config"

# ---------------------------------------------------------------------------
# 4. PID namespace isolation
# ---------------------------------------------------------------------------
header "PID Namespace Isolation"

visible_pids=$(ps -e --no-headers 2>/dev/null | wc -l)
if [ "$visible_pids" -lt 20 ]; then
    pass "Only $visible_pids processes visible (PID namespace is isolated)"
else
    warn "$visible_pids processes visible — PID namespace may not be isolated"
fi

# PID 1 inside the namespace should be bwrap or the shell, not systemd
pid1_name=$(ps -p 1 -o comm= 2>/dev/null || echo "unknown")
if [ "$pid1_name" = "systemd" ] || [ "$pid1_name" = "init" ]; then
    fail "PID 1 is $pid1_name — not in a PID namespace"
else
    pass "PID 1 is '$pid1_name' (not host init — PID namespace active)"
fi

# ---------------------------------------------------------------------------
# 5. Git push blocked
# ---------------------------------------------------------------------------
header "Git Push Blocked"

git_push_output=$(git push 2>&1 || true)
if echo "$git_push_output" | grep -qi "blocked"; then
    pass "git push is blocked"
else
    # Could also fail for other reasons (no remote, etc.), check if wrapper is in PATH
    git_path=$(which git 2>/dev/null || echo "")
    if echo "$git_path" | grep -q "agent-sandbox"; then
        pass "git wrapper is active at $git_path (push likely blocked)"
    else
        warn "git push did not show 'blocked' message — wrapper may not be in PATH (git=$git_path)"
    fi
fi

# Verify git commit still works (non-destructive — we use --dry-run if available)
if git rev-parse --is-inside-work-tree &>/dev/null; then
    # We're in a git repo; verify basic git ops work
    if git status &>/dev/null; then
        pass "git status works"
    else
        fail "git status broken"
    fi
else
    warn "Not inside a git repo — skipping git operation tests"
fi

# ---------------------------------------------------------------------------
# 6. Gitconfig sanitized
# ---------------------------------------------------------------------------
header "Gitconfig Sanitization"

gitconfig_content=$(git config --global --list 2>/dev/null || echo "")
if echo "$gitconfig_content" | grep -qi "credential"; then
    critical_fail "Credential helpers found in gitconfig"
else
    pass "No credential helpers in gitconfig"
fi

if echo "$gitconfig_content" | grep -qi 'url.*insteadof'; then
    fail "URL rewrites found in gitconfig (may leak credentials)"
else
    pass "No URL rewrites in gitconfig"
fi

push_default=$(git config --global push.default 2>/dev/null || echo "")
if [ "$push_default" = "nothing" ]; then
    pass "push.default = nothing (safety override active)"
else
    warn "push.default = '$push_default' (expected 'nothing')"
fi

# ---------------------------------------------------------------------------
# 7. Environment isolation
# ---------------------------------------------------------------------------
header "Environment Isolation"

SECRET_VARS=(
    "ANTHROPIC_API_KEY"
    "OPENAI_API_KEY"
    "AWS_SECRET_ACCESS_KEY"
    "AWS_SESSION_TOKEN"
    "GITHUB_TOKEN"
    "GH_TOKEN"
    "GITLAB_TOKEN"
    "NPM_TOKEN"
    "DOCKER_PASSWORD"
    "DATABASE_URL"
    "PRIVATE_KEY"
)

leaked=0
for var in "${SECRET_VARS[@]}"; do
    val="${!var:-}"
    if [ -n "$val" ]; then
        critical_fail "Secret env var $var is set (${#val} chars)"
        ((leaked++))
    fi
done
if [ "$leaked" -eq 0 ]; then
    pass "No common secret env vars leaked (checked ${#SECRET_VARS[@]} vars)"
fi

# Verify expected vars ARE set
for var in HOME USER SHELL PATH; do
    val="${!var:-}"
    if [ -n "$val" ]; then
        pass "$var is set ($val)"
    else
        fail "$var is NOT set (expected by sandbox)"
    fi
done

# ---------------------------------------------------------------------------
# 8. Network (informational — sandbox does NOT block network)
# ---------------------------------------------------------------------------
header "Network (informational)"

if command -v curl &>/dev/null; then
    if curl -s --max-time 5 -o /dev/null -w '%{http_code}' https://example.com | grep -q "200"; then
        warn "Network access is available (by design — agent needs API access)"
    else
        pass "Network appears restricted or unreachable"
    fi
elif command -v wget &>/dev/null; then
    if wget -q --timeout=5 -O /dev/null https://example.com 2>/dev/null; then
        warn "Network access is available (by design — agent needs API access)"
    else
        pass "Network appears restricted or unreachable"
    fi
else
    warn "No curl or wget — cannot test network"
fi

# ---------------------------------------------------------------------------
# 9. /tmp isolation
# ---------------------------------------------------------------------------
header "Temp Directory Isolation"

# /tmp should be a sandbox-local tmpfs
TMP_TEST="/tmp/.sandbox-tmp-test-$$"
if touch "$TMP_TEST" 2>/dev/null; then
    rm -f "$TMP_TEST"
    # Check if /tmp is a tmpfs
    tmp_mount=$(mount 2>/dev/null | grep " /tmp " || true)
    if echo "$tmp_mount" | grep -q tmpfs; then
        pass "/tmp is an isolated tmpfs"
    else
        warn "/tmp is writable but could not confirm it is a separate tmpfs"
    fi
else
    pass "/tmp is not writable"
fi

# ---------------------------------------------------------------------------
# 10. Device and proc
# ---------------------------------------------------------------------------
header "Device and Proc Mounts"

if [ -e /dev/null ] && [ -c /dev/null ]; then
    pass "/dev/null exists and is a character device"
else
    fail "/dev/null missing or wrong type"
fi

if [ -r /proc/self/status ]; then
    pass "/proc is mounted and readable"
else
    fail "/proc is not accessible"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
printf '\n\033[1;36m══ Summary ══\033[0m\n'
printf '  \033[32m✓ Passed:  %d\033[0m\n' "$PASS"
printf '  \033[33m⚠ Warned:  %d\033[0m\n' "$WARN"
printf '  \033[31m✗ Failed:  %d\033[0m\n' "$FAIL"

if [ "$CRITICAL_FAIL" -gt 0 ]; then
    printf '\n  \033[31;1m⚠ %d CRITICAL failure(s) — sandbox may not be effective!\033[0m\n\n' "$CRITICAL_FAIL"
    exit 1
elif [ "$FAIL" -gt 0 ]; then
    printf '\n  \033[33mSome non-critical tests failed — review above.\033[0m\n\n'
    exit 1
else
    printf '\n  \033[32mAll tests passed — sandbox isolation looks good.\033[0m\n\n'
    exit 0
fi
