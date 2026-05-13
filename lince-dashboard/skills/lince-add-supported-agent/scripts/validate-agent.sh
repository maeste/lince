#!/usr/bin/env bash
# validate-agent.sh -- Validate an agent registration produced by the
# lince-add-supported-agent skill against the m-15 contract.
#
# Usage: validate-agent.sh <agent-key>
#
# Exits 0 on PASS, 1 on FAIL.

set -uo pipefail

KEY="${1:?Usage: validate-agent.sh <agent-key>}"

SANDBOX_CONFIG="$HOME/.agent-sandbox/config.toml"
DASHBOARD_CONFIG="$HOME/.config/lince-dashboard/agents-defaults.toml"
HOOK_DIR="$HOME/.local/share/lince/hooks"

CANONICAL_EVENTS="running input permission stopped"

fail_count=0
warn_count=0

note() { printf '  %s\n' "$*"; }
ok()   { printf '  [OK]   %s\n' "$*"; }
warn() { printf '  [WARN] %s\n' "$*"; warn_count=$((warn_count + 1)); }
err()  { printf '  [FAIL] %s\n' "$*"; fail_count=$((fail_count + 1)); }

require_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        err "python3 is required for TOML parsing but was not found in PATH"
        exit 1
    fi
}

# Parse a TOML file and emit a small JSON-ish summary for the requested
# agent key. Echoes:
#   exists=<true|false>
#   has_native_hooks=<true|false|missing>
#   command=<binary-or-empty>
#   event_map=<space-separated values, or empty>
parse_toml() {
    local file="$1"
    local key="$2"
    python3 - "$file" "$key" <<'PY'
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

path, key = sys.argv[1], sys.argv[2]
try:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
except FileNotFoundError:
    print("__missing__")
    sys.exit(0)
except Exception as exc:
    print(f"__parse_error__:{exc}")
    sys.exit(0)

agents = data.get("agents", {})
section = agents.get(key)
print("exists=" + ("true" if section is not None else "false"))
if section is None:
    sys.exit(0)

import shlex

def emit(name, value):
    print(f"{name}={shlex.quote(str(value))}")

cmd = section.get("command")
if isinstance(cmd, list):
    emit("command", cmd[0] if cmd else "")
elif isinstance(cmd, str):
    emit("command", cmd)
else:
    emit("command", "")

if "has_native_hooks" in section:
    emit("has_native_hooks", "true" if section["has_native_hooks"] else "false")
else:
    emit("has_native_hooks", "missing")

em = section.get("event_map") or {}
emit("event_map", " ".join(str(v) for v in em.values()))
PY
}

require_python

echo "Validating agent '$KEY'"
echo

# ---------------------------------------------------------------------------
# 1. Sandbox config
# ---------------------------------------------------------------------------
echo "Sandbox config: $SANDBOX_CONFIG"
if [[ ! -f "$SANDBOX_CONFIG" ]]; then
    err "file not found"
else
    parsed=$(parse_toml "$SANDBOX_CONFIG" "$KEY")
    case "$parsed" in
        __parse_error__:*) err "TOML parse error: ${parsed#__parse_error__:}" ;;
        __missing__)       err "file not found (race)" ;;
        *)
            eval "$parsed"   # exists, command (no has_native_hooks here)
            if [[ "${exists:-false}" != "true" ]]; then
                err "[agents.$KEY] section not present"
            else
                ok "[agents.$KEY] section found"
                if [[ -n "${command:-}" ]]; then
                    if command -v "$command" >/dev/null 2>&1; then
                        ok "binary '$command' is on PATH ($(command -v "$command"))"
                    else
                        warn "binary '$command' not found on PATH (may resolve inside sandbox)"
                    fi
                else
                    err "command field is empty or missing"
                fi
            fi
            ;;
    esac
fi
echo

# ---------------------------------------------------------------------------
# 2. Dashboard config
# ---------------------------------------------------------------------------
echo "Dashboard config: $DASHBOARD_CONFIG"
dash_has_native_hooks="missing"
dash_event_map=""
if [[ ! -f "$DASHBOARD_CONFIG" ]]; then
    err "file not found"
else
    parsed=$(parse_toml "$DASHBOARD_CONFIG" "$KEY")
    case "$parsed" in
        __parse_error__:*) err "TOML parse error: ${parsed#__parse_error__:}" ;;
        __missing__)       err "file not found (race)" ;;
        *)
            # shellcheck disable=SC2086
            # reset vars between sources
            exists=false; command=""; has_native_hooks="missing"; event_map=""
            eval "$parsed"
            if [[ "${exists:-false}" != "true" ]]; then
                err "[agents.$KEY] section not present"
            else
                ok "[agents.$KEY] section found"
                dash_has_native_hooks="${has_native_hooks:-missing}"
                dash_event_map="${event_map:-}"
                case "$dash_has_native_hooks" in
                    true)  ok "has_native_hooks = true (Tier A)" ;;
                    false) ok "has_native_hooks = false (Tier B)" ;;
                    *)     err "has_native_hooks field is missing" ;;
                esac
            fi
            ;;
    esac
fi
echo

# ---------------------------------------------------------------------------
# 3. Tier-specific checks
# ---------------------------------------------------------------------------
hook_sh="$HOOK_DIR/${KEY}-status-hook.sh"
hook_ts="$HOOK_DIR/${KEY}-status-hook.ts"
hook_js="$HOOK_DIR/${KEY}-status-hook.js"

found_hook=""
for h in "$hook_sh" "$hook_ts" "$hook_js"; do
    [[ -f "$h" ]] && { found_hook="$h"; break; }
done

if [[ "$dash_has_native_hooks" == "true" ]]; then
    echo "Tier A checks"
    if [[ -z "$found_hook" ]]; then
        err "has_native_hooks=true but no hook script at $HOOK_DIR/${KEY}-status-hook.{sh,ts,js}"
    else
        ok "hook script: $found_hook"
        if [[ ! -x "$found_hook" ]]; then
            warn "hook script is not executable (chmod +x needed)"
        fi
        if [[ "$found_hook" == *.sh ]]; then
            if bash -n "$found_hook" 2>/dev/null; then
                ok "bash -n syntax check passed"
            else
                err "bash -n syntax check failed"
                bash -n "$found_hook" 2>&1 | sed 's/^/         /'
            fi
        fi
    fi

    if [[ -z "$dash_event_map" ]]; then
        err "has_native_hooks=true but [agents.$KEY.event_map] is empty or missing"
    else
        bad=""
        for v in $dash_event_map; do
            case " $CANONICAL_EVENTS " in
                *" $v "*) ;;
                *) bad="$bad $v" ;;
            esac
        done
        if [[ -z "$bad" ]]; then
            ok "event_map values are all canonical ($dash_event_map)"
        else
            err "event_map contains non-canonical values:${bad}. Allowed: $CANONICAL_EVENTS"
        fi
    fi
elif [[ "$dash_has_native_hooks" == "false" ]]; then
    echo "Tier B checks"
    if [[ -n "$found_hook" ]]; then
        warn "has_native_hooks=false but hook script exists at $found_hook (will be ignored)"
    else
        ok "no hook script (as expected for Tier B)"
    fi
    if [[ -n "$dash_event_map" ]]; then
        warn "has_native_hooks=false but event_map is populated (will be ignored)"
    else
        ok "no event_map (as expected for Tier B)"
    fi
else
    note "Skipping tier-specific checks (has_native_hooks could not be determined)"
fi
echo

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
if [[ "$fail_count" -eq 0 ]]; then
    if [[ "$warn_count" -eq 0 ]]; then
        echo "Result: PASS"
    else
        echo "Result: PASS (with $warn_count warning(s))"
    fi
    exit 0
else
    echo "Result: FAIL ($fail_count error(s), $warn_count warning(s))"
    exit 1
fi
