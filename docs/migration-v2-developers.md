# Migrating to Config v2 (developers)

For contributors, skill authors, and integrators. Rationale and full
contracts: [design doc](design/config-v2-design.md). Key tables:
[generated configuration reference](documentation/configuration-keys.md).

## The contracts at a glance

| Artifact | Owner | Contract |
|---|---|---|
| `registry.d/<agent>.toml` + `providers.toml` | **shipped** | One file per agent; always overwritten on update; generated from the legacy agents-defaults files by `scripts/gen_registry.py` until those are deleted (diff-guard: `scripts/tests/test_registry_sync.py`) |
| `~/.config/lince/lince.toml` | **user** | Versioned (`version = "2.0"`, §2.1 contract), default-deny, never touched by update |
| `<project>/.lince/lince.toml` | **project** | Same schema, no `version`, security keys clamped (loosening needs `[trust.projects."…"]`) |
| `lince-config resolve --json` | **the only read API** | Requested view; secrets never cross (env-var names only) |
| `<id>.policy.json` (next to `.state`) | runner | **Enforced** view, per launch (§4.3.1) — paranoid fails closed on degradation (I7) |

## Adding an agent: before → after

| | Before | After (#204) |
|---|---|---|
| Files to edit | 4 (two agents-defaults, profiles fragment, nono profile) | **1** registry file (+ optional hook) |
| Pi-style env bundle | copy-pasted 4× | `provider_env = "all"` (expands from `providers.toml`) |
| `-unsandboxed` variant | duplicated entry incl. event_map | derived (§3.5); exceptions in `[variants.unsandboxed]` |
| Until legacy files are deleted | — | edit the legacy files and run `python3 scripts/gen_registry.py` (the diff-guard enforces sync) |

## What is removed, and when

| Legacy surface | Replacement | Removal |
|---|---|---|
| Dashboard TOML parsing of sandbox-owned files (`parse_providers_from_toml`, level globs, `load_agent_defaults_async`) | `resolve --json` | **removed** (#202) |
| `~/.local/bin/agents-defaults.toml` double install | registry.d | **removed** (#204) |
| quickstart awk-filtered agents-defaults rewrites | `lince-config apply` + `[dashboard].enabled_agents` | **removed** (#207) |
| Python `[profiles.*]` / `default_profile` aliases (`resolve_providers`) | `migrate-providers` rewrite | window close (2.2, §5.6) |
| Rust `serde(alias = "profiles")` etc. | resolve --json shapes | window close (2.2) |
| Legacy shipped `agents-defaults.toml` files in repo | registry.d as hand-maintained source | when the dual-read window closes |

## Rules for new config keys

1. **Schema-first**: add the key to the embedded schema in `lince-config`
   (with `description` + `default`) → `lince-config schema --write schemas/`
   → `python3 scripts/gen_config_reference.py`. The reference and editor
   support regenerate; `scripts/tests/test_schemas.py` +
   `test_config_reference.py` fail on drift.
2. **Default-deny**: a new policy field must not widen any boundary when
   absent.
3. **Version bump**: a key the old parser must not silently ignore ⇒ bump
   the minor (`SCHEMA_VERSION_NATIVE`); the §2.1 contract handles the window.
4. Shipped examples must validate clean: `scripts/tests/test_schemas.py`
   checks every example/template with zero errors *and* zero warnings.

## Skill authors

- Write configuration ONLY through `lince-config apply` / `lince-config set
  --target lince` / `validate` — never edit TOML files directly, never write
  into `registry.d/` or `agents-defaults.toml`.
- Validate your result: `lince-config resolve --agent <name>` fails that
  agent only, with a named-key diagnostic.
- Machine surfaces: `lince-config templates --json`, `discover --json`,
  `resolve --json`.

## Test entry points

```bash
python3 scripts/tests/test_registry_sync.py      # registry ↔ legacy parity
python3 scripts/tests/test_schemas.py            # schemas + shipped examples
python3 scripts/tests/test_resolve.py            # resolver semantics
python3 scripts/tests/test_apply.py              # composition engine
python3 scripts/tests/test_policy_record.py      # effective-policy record
bash sandbox/tests/test-landlock-exec.sh         # Landlock fence gate
cd lince-dashboard/plugin && cargo build --target wasm32-wasip1
```
