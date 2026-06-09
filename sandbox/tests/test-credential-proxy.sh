#!/usr/bin/env bash
# test-credential-proxy.sh — Unit tests for _collect_proxy_rules (#194 / #195).
#
# Rules enforced:
#   1. At most one credential rule per domain; on conflict an
#      Authorization/Bearer rule REPLACES a non-Authorization rule
#      (Bearer wins over x-api-key, #194).
#   2. Same-header-type conflicts keep the first match (dict order),
#      e.g. ANTHROPIC_AUTH_TOKEN wins over CLAUDE_CODE_OAUTH_TOKEN.
#   3. CLAUDE_CODE_OAUTH_TOKEN is recognized as a Bearer alias for
#      api.anthropic.com (#195).
#   4. strip_vars always contains ALL matched env vars, even when their
#      rule lost the per-domain conflict.
#   5. Rules for other providers (OPENAI/GOOGLE) are unaffected.
#
# Exit code:
#   0 — all assertions pass
#   1 — at least one failure

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX_DIR="$(dirname "$SCRIPT_DIR")"
AGENT_SANDBOX="${SANDBOX_DIR}/agent-sandbox"

if [ ! -f "$AGENT_SANDBOX" ]; then
    echo "FAIL: agent-sandbox not found at $AGENT_SANDBOX"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: python3 required"
    exit 1
fi

python3 - "$AGENT_SANDBOX" <<'PY'
import importlib.machinery
import importlib.util
import sys

script_path = sys.argv[1]

# The script has no .py extension — SourceFileLoader handles that.
loader = importlib.machinery.SourceFileLoader("agent_sandbox", script_path)
spec = importlib.util.spec_from_loader("agent_sandbox", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

collect = mod._collect_proxy_rules

failures = []
passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    if cond:
        passed += 1
        print(f"  ok: {name}")
    else:
        failures.append(name)
        print(f"  FAIL: {name}" + (f" — {detail}" if detail else ""))


def rules_for(rules, domain):
    return [r for r in rules if r["domain"] == domain]


# (a) ANTHROPIC_API_KEY + ANTHROPIC_AUTH_TOKEN => one Authorization rule (#194)
print("case a: ANTHROPIC_API_KEY + ANTHROPIC_AUTH_TOKEN")
rules, strip = collect({
    "ANTHROPIC_API_KEY": "sk-ant-api-key",
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-bearer",
})
anth = rules_for(rules, "api.anthropic.com")
check("single rule for api.anthropic.com", len(anth) == 1, f"got {len(anth)}")
check("header_name is Authorization", anth and anth[0]["header_name"] == "Authorization")
check("value comes from ANTHROPIC_AUTH_TOKEN", anth and anth[0]["header_value"] == "sk-ant-bearer")
check("header_prefix is 'Bearer '", anth and anth[0]["header_prefix"] == "Bearer ")
check("both vars in strip_vars", set(strip) == {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"}, f"got {strip}")

# (b) only ANTHROPIC_API_KEY => x-api-key rule
print("case b: only ANTHROPIC_API_KEY")
rules, strip = collect({"ANTHROPIC_API_KEY": "sk-ant-api-key"})
check("exactly one rule", len(rules) == 1, f"got {len(rules)}")
check("header_name is x-api-key", rules and rules[0]["header_name"] == "x-api-key")
check("value from ANTHROPIC_API_KEY", rules and rules[0]["header_value"] == "sk-ant-api-key")
check("strip_vars == [ANTHROPIC_API_KEY]", strip == ["ANTHROPIC_API_KEY"], f"got {strip}")

# (c) only CLAUDE_CODE_OAUTH_TOKEN => Authorization rule + var stripped (#195)
print("case c: only CLAUDE_CODE_OAUTH_TOKEN")
rules, strip = collect({"CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat-123"})
check("exactly one rule", len(rules) == 1, f"got {len(rules)}")
check("domain is api.anthropic.com", rules and rules[0]["domain"] == "api.anthropic.com")
check("header_name is Authorization", rules and rules[0]["header_name"] == "Authorization")
check("header_prefix is 'Bearer '", rules and rules[0]["header_prefix"] == "Bearer ")
check("value from CLAUDE_CODE_OAUTH_TOKEN", rules and rules[0]["header_value"] == "sk-ant-oat-123")
check("CLAUDE_CODE_OAUTH_TOKEN in strip_vars", "CLAUDE_CODE_OAUTH_TOKEN" in strip, f"got {strip}")

# (d) ANTHROPIC_AUTH_TOKEN + CLAUDE_CODE_OAUTH_TOKEN => keep first (Bearer tie)
print("case d: ANTHROPIC_AUTH_TOKEN + CLAUDE_CODE_OAUTH_TOKEN")
rules, strip = collect({
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-bearer",
    "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat-123",
})
check("exactly one rule", len(rules) == 1, f"got {len(rules)}")
check("value from ANTHROPIC_AUTH_TOKEN", rules and rules[0]["header_value"] == "sk-ant-bearer")
check("env_var is ANTHROPIC_AUTH_TOKEN", rules and rules[0]["env_var"] == "ANTHROPIC_AUTH_TOKEN")
check("both vars in strip_vars", set(strip) == {"ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"}, f"got {strip}")

# (d2) #113/#194 reproduction: ANTHROPIC_API_KEY + CLAUDE_CODE_OAUTH_TOKEN => Bearer wins
print("case d2: ANTHROPIC_API_KEY + CLAUDE_CODE_OAUTH_TOKEN")
rules, strip = collect({
    "ANTHROPIC_API_KEY": "sk-ant-api-key",
    "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat-123",
})
check("exactly one rule", len(rules) == 1, f"got {len(rules)}")
check("header_name is Authorization", rules and rules[0]["header_name"] == "Authorization")
check("value from CLAUDE_CODE_OAUTH_TOKEN", rules and rules[0]["header_value"] == "sk-ant-oat-123")
check("both vars in strip_vars", set(strip) == {"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"}, f"got {strip}")

# (e) all three anthropic vars => one rule, ANTHROPIC_AUTH_TOKEN wins, all stripped
print("case e: all three anthropic vars")
rules, strip = collect({
    "ANTHROPIC_API_KEY": "sk-ant-api-key",
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-bearer",
    "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat-123",
})
check("exactly one rule", len(rules) == 1, f"got {len(rules)}")
check("value from ANTHROPIC_AUTH_TOKEN", rules and rules[0]["header_value"] == "sk-ant-bearer")
check(
    "all three vars in strip_vars",
    set(strip) == {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"},
    f"got {strip}",
)

# (f) OPENAI / GOOGLE rules unaffected by anthropic conflict resolution
print("case f: other providers unaffected")
rules, strip = collect({
    "ANTHROPIC_API_KEY": "sk-ant-api-key",
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-bearer",
    "OPENAI_API_KEY": "sk-openai",
    "GOOGLE_API_KEY": "goog-key",
    "GOOGLE_BASE_URL": "https://my-proxy.example.com",
})
openai = rules_for(rules, "api.openai.com")
goog = rules_for(rules, "generativelanguage.googleapis.com")
check("one openai rule", len(openai) == 1)
check("openai Authorization Bearer", openai and openai[0]["header_name"] == "Authorization"
      and openai[0]["header_prefix"] == "Bearer " and openai[0]["header_value"] == "sk-openai")
check("one google rule", len(goog) == 1)
check("google x-goog-api-key", goog and goog[0]["header_name"] == "x-goog-api-key"
      and goog[0]["header_value"] == "goog-key")
check("google upstream_base captured", goog and goog[0]["upstream_base"] == "https://my-proxy.example.com")
check("3 rules total (one per domain)", len(rules) == 3, f"got {len(rules)}")
check(
    "all matched vars in strip_vars",
    set(strip) == {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "GOOGLE_API_KEY"},
    f"got {strip}",
)

# (f2) GOOGLE_API_KEY + GEMINI_API_KEY => same header type, keep first
print("case f2: GOOGLE_API_KEY + GEMINI_API_KEY keep-first")
rules, strip = collect({"GOOGLE_API_KEY": "goog-key", "GEMINI_API_KEY": "gem-key"})
check("exactly one rule", len(rules) == 1, f"got {len(rules)}")
check("value from GOOGLE_API_KEY", rules and rules[0]["header_value"] == "goog-key")
check("both vars in strip_vars", set(strip) == {"GOOGLE_API_KEY", "GEMINI_API_KEY"}, f"got {strip}")

# (g) empty values are dropped entirely
print("case g: empty values dropped")
rules, strip = collect({"ANTHROPIC_API_KEY": "", "CLAUDE_CODE_OAUTH_TOKEN": ""})
check("no rules", rules == [])
check("no strip_vars", strip == [])

print()
if failures:
    print(f"FAIL: {len(failures)} assertion(s) failed, {passed} passed")
    sys.exit(1)
print(f"PASS: {passed} assertions")
PY
exit $?
