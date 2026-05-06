use std::collections::{BTreeMap, HashMap};
use std::path::PathBuf;

use zellij_tile::prelude::*;

use crate::config::{
    shell_escape, AgentLayout, AgentTypeConfig, DashboardConfig, DEFAULT_SANDBOX_COMMAND,
};
use crate::sandbox_backend::SandboxBackend;

/// Name of the lifecycle wrapper script for agents without native hooks.
const AGENT_WRAPPER: &str = "lince-agent-wrapper";
use crate::types::{AgentInfo, AgentStatus};

/// Variant suffixes stripped by `agent_type_base_name()`.
/// Add new suffixes here when new sandbox variants are introduced.
const AGENT_TYPE_SUFFIXES: &[&str] = &[
    "-unsandboxed",
    "-bwrap",
    "-nono",
    "-paranoid",
    "-permissive",
];

/// Extract base agent type name, stripping sandbox variant suffixes.
/// e.g. "claude-unsandboxed" → "claude", "codex-bwrap" → "codex", "gemini" → "gemini".
pub fn agent_type_base_name(agent_type: &str) -> &str {
    for suffix in AGENT_TYPE_SUFFIXES {
        if let Some(base) = agent_type.strip_suffix(suffix) {
            return base;
        }
    }
    agent_type
}

/// Glyph for a sandbox isolation level. Fixed mapping (not user-overridable),
/// kept stable so the visual cue on a pane title stays consistent even when
/// the wizard's color palette is customized. Unknown levels get a neutral
/// square so custom levels don't break the layout.
pub fn sandbox_level_glyph(level: &str) -> &'static str {
    match level {
        "paranoid" => "\u{1F7E2}",   // 🟢
        "normal" => "\u{1F535}",     // 🔵
        "permissive" => "\u{1F7E1}", // 🟡
        _ => "\u{26AA}",             // ⚪
    }
}

/// Build pane title with a sandbox-level indicator.
///
/// - Non-sandboxed agent types: `[NON-SANDBOXED] <name>` (unchanged).
/// - Sandboxed with a known level: `<glyph> [<level>] <name>`, e.g. `🟢 [paranoid] agent-1`.
///   The level is taken from `sandbox_level_override` (runtime wizard selection) first,
///   then falls back to the TOML-pinned `sandbox_level` for the agent type.
/// - Sandboxed with no level anywhere (legacy static command): `<name>` (unchanged).
pub fn pane_title(
    name: &str,
    agent_type: &str,
    agent_types: &HashMap<String, AgentTypeConfig>,
    sandbox_level_override: Option<&str>,
) -> String {
    let cfg = agent_types.get(agent_type);
    let sandboxed = cfg.map_or(true, |c| c.sandboxed);
    if !sandboxed {
        return format!("[NON-SANDBOXED] {}", name);
    }
    let level = sandbox_level_override
        .or_else(|| cfg.and_then(|c| c.sandbox_level.as_deref()));
    match level {
        Some(level) => format!("{} [{}] {}", sandbox_level_glyph(level), level, name),
        None => name.to_string(),
    }
}

/// Default floating pane coordinates for agent panes (80% x 85%, centered).
pub fn default_agent_pane_coords() -> FloatingPaneCoordinates {
    FloatingPaneCoordinates::default()
        .with_x_percent(20)
        .with_y_percent(5)
        .with_width_percent(80)
        .with_height_percent(85)
}

use crate::config::now_secs;

/// Apply placeholder substitution to a command template.
/// Replaces `{agent_id}`, `{project_dir}`, `{profile}` in each arg.
fn expand_command_template(
    template: &[String],
    agent_id: &str,
    project_dir: &str,
    profile: Option<&str>,
) -> Vec<String> {
    template
        .iter()
        .map(|arg| {
            arg.replace("{agent_id}", agent_id)
                .replace("{project_dir}", project_dir)
                .replace("{profile}", profile.unwrap_or(""))
        })
        .collect()
}

/// Resolve the nono profile filename for an agent at a given sandbox level.
///
/// `normal` maps to the base profile (`lince-<agent>`); any other value
/// becomes a suffixed profile (`lince-<agent>-<level>`). This is intentionally
/// a free-form mapping so users can drop a custom profile at
/// `~/.config/nono/profiles/lince-<agent>-<custom>.json` and reference it via
/// `sandbox_level = "<custom>"` without any plugin changes.
pub fn resolve_nono_profile(agent_type: &str, level: &str) -> String {
    if level == "normal" {
        format!("lince-{}", agent_type)
    } else {
        format!("lince-{}-{}", agent_type, level)
    }
}

/// Synthesize the command template for a sandboxed agent based on the
/// (backend, level) pair. Returns `None` if the agent type doesn't yet have
/// a known inner-command shape (follow-up tasks add agents incrementally).
///
/// `agent_id` and `project_dir` are baked in directly: the
/// non-bash-wrapper branches (bwrap, normal nono) emit them as separate
/// argv elements where shell parsing doesn't apply, and the paranoid
/// nono bash wrapper substitutes them with `shell_quote()` so paths
/// containing whitespace, `"`, or `$` can't break the wrapper or open a
/// shell-injection surface (defense-in-depth: project_dir comes from
/// local UI, but quoting costs nothing).
///
/// The returned argv is final — no more placeholder substitution needed
/// downstream.
fn synthesize_sandboxed_command(
    agent_type: &str,
    backend: &SandboxBackend,
    level: &str,
    agent_id: &str,
    project_dir: &str,
) -> Option<Vec<String>> {
    let base = agent_type_base_name(agent_type);
    // Per-agent dispatch: (inner argv, $HOME subdir for the paranoid scratch).
    // codex's `--sandbox danger-full-access` disables its own filesystem
    // sandbox so it doesn't fight ours; the bwrap path also reads
    // disable_inner_sandbox_args from agents-defaults.toml.
    let (inner_command, agent_home_subdir): (Vec<String>, &str) = match base {
        "claude" => (
            vec![
                "claude".to_string(),
                "--dangerously-skip-permissions".to_string(),
            ],
            ".claude",
        ),
        "codex" => (
            vec![
                "codex".to_string(),
                "--full-auto".to_string(),
                "--sandbox".to_string(),
                "danger-full-access".to_string(),
            ],
            ".codex",
        ),
        "gemini" => (vec!["gemini".to_string()], ".gemini"),
        // Bun-based binaries SIGABRT when spawned under Landlock, so
        // resolve and exec the native .opencode to skip the Node
        // launcher's spawnSync.
        "opencode" => (
            vec![
                "bash".to_string(),
                "-c".to_string(),
                "exec \"$(dirname \"$(readlink -f \"$(which opencode)\")\")/.opencode\" \"$@\""
                    .to_string(),
                "--".to_string(),
            ],
            ".config/opencode",
        ),
        "pi" => (vec!["pi".to_string()], ".pi"),
        _ => return None,
    };

    let nono_profile = resolve_nono_profile(base, level);

    Some(match backend {
        SandboxBackend::AgentSandbox => {
            let mut cmd = vec![
                "agent-sandbox".to_string(),
                "run".to_string(),
                "-p".to_string(),
                project_dir.to_string(),
                "--id".to_string(),
                agent_id.to_string(),
                "--agent".to_string(),
                base.to_string(),
            ];
            if level != "normal" {
                cmd.push("--sandbox-level".to_string());
                cmd.push(level.to_string());
            }
            cmd
        }
        SandboxBackend::Nono => {
            let inner_str = inner_command
                .iter()
                .map(|s| shell_quote(s))
                .collect::<Vec<_>>()
                .join(" ");
            if level == "paranoid" {
                // Bash wrapper: rsync ~/.<agent>/ into a scratch under
                // $XDG_RUNTIME_DIR, run nono with HOME=scratch, rm scratch
                // on EXIT. No `exec` so the EXIT trap fires. Caller-supplied
                // values are shell_quote'd before substitution.
                let bash = format!(
                    "set -e; \
                     SCRATCH=\"${{XDG_RUNTIME_DIR:-/tmp}}/lince-{agent_id}\"; \
                     mkdir -p -- \"$SCRATCH/{home_subdir}\"; \
                     trap 'rm -rf -- \"$SCRATCH\"' EXIT; \
                     if [ -d \"$HOME/{home_subdir}\" ]; then \
                       rsync -a --delete -- \"$HOME/{home_subdir}/\" \"$SCRATCH/{home_subdir}/\"; \
                     fi; \
                     HOME=\"$SCRATCH\" nono run --profile {nono_profile} --workdir {project_dir} -- {inner}",
                    agent_id = shell_quote(agent_id),
                    home_subdir = agent_home_subdir,
                    nono_profile = shell_quote(&nono_profile),
                    project_dir = shell_quote(project_dir),
                    inner = inner_str,
                );
                vec!["bash".to_string(), "-c".to_string(), bash]
            } else {
                let mut cmd = vec![
                    "nono".to_string(),
                    "run".to_string(),
                    "--profile".to_string(),
                    nono_profile,
                    "--workdir".to_string(),
                    project_dir.to_string(),
                    "--".to_string(),
                ];
                cmd.extend(inner_command);
                cmd
            }
        }
        SandboxBackend::None => inner_command,
    })
}

/// POSIX shell quoting for embedding strings inside `bash -c '...'`
/// wrappers. Strings containing only alphanumerics and a few obviously
/// safe punctuation chars pass through unchanged for readability;
/// anything else is wrapped in single quotes, with embedded single
/// quotes escaped via the standard `'\''` idiom that lives in
/// `shell_escape`.
fn shell_quote(s: &str) -> String {
    if s.chars()
        .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '/' | '.' | ':'))
    {
        s.to_string()
    } else {
        format!("'{}'", shell_escape(s))
    }
}

/// Internal helper that does the actual spawn work.
/// All public spawn functions resolve their parameters and delegate here.
fn spawn_inner(
    config: &DashboardConfig,
    next_id: &mut u32,
    agents: &[AgentInfo],
    name: String,
    agent_type: &str,
    profile: Option<String>,
    project_dir: String,
    group: Option<String>,
    sandbox_level_override: Option<String>,
    sandbox_backend_override: Option<SandboxBackend>,
) -> Result<AgentInfo, String> {
    if agents.len() >= config.max_agents {
        return Err(format!(
            "Max agents reached ({}). Kill one first.",
            config.max_agents
        ));
    }

    *next_id += 1;
    let base = agent_type_base_name(agent_type);
    let id = format!("{}-{}", base, next_id);
    let name = if name.is_empty() { id.clone() } else { name };

    // Validate profile: drop it if it doesn't exist for this agent type.
    // Prevents failures when e.g. default_profile is "anthropic" but a codex
    // agent has no such profile, or when restoring a saved agent whose profile
    // was removed from config.
    let profile = profile.and_then(|p| {
        let available = config.profiles_for_agent_type(agent_type);
        if available.iter().any(|a| a == &p) { Some(p) } else { None }
    });

    let args: Vec<String> = if let Some(type_config) = config.agent_types.get(agent_type) {
        let mut expanded: Vec<String> = Vec::new();

        // For non-sandboxed agents, apply profile env vars via `env` command.
        // Sandboxed agents go through agent-sandbox which handles env internally.
        if !type_config.sandboxed {
            // Unset conflicting env vars from profile
            if let Some(ref prof_name) = profile {
                if let Some(details) = config.profile_details_for(agent_type, prof_name) {
                    for var in &details.env_unset {
                        expanded.push("-u".to_string());
                        expanded.push(var.clone());
                    }
                    for (k, v) in &details.env {
                        expanded.push(format!("{}={}", k, v));
                    }
                }
            }
            // Agent-type env vars (e.g. API keys)
            for (k, v) in &type_config.env_vars {
                expanded.push(format!("{}={}", k, v));
            }
        }

        expanded.push(format!("LINCE_AGENT_ID={}", id));
        // If agent doesn't have native hooks, wrap with lince-agent-wrapper
        if !type_config.has_native_hooks {
            expanded.push(AGENT_WRAPPER.to_string());
            expanded.push(id.clone());
            expanded.push(type_config.status_pipe_name.clone());
        }
        // When `sandbox_level` is set, synthesize the command from
        // (agent_type, backend, level) instead of using the static template.
        // This is what enables the single-entry-per-agent model in
        // agents-defaults.toml.
        // Two paths produce the agent command: synthesize_sandboxed_command
        // bakes agent_id/project_dir directly into argv (with shell_quote
        // for values that end up inside a bash wrapper), so its output is
        // final and skips expand_command_template. The legacy/static path
        // (no sandbox_level set, or agent type not yet covered) goes
        // through the placeholder-substitution helper as before.
        // Runtime override takes precedence over the TOML-pinned sandbox_level.
        let effective_level = sandbox_level_override.as_deref()
            .or_else(|| type_config.sandbox_level.as_deref());
        // Same precedence rule for sandbox_backend.
        let effective_backend = sandbox_backend_override
            .as_ref()
            .unwrap_or(&type_config.sandbox_backend);
        let synthesized = effective_level.and_then(|level| {
            synthesize_sandboxed_command(
                agent_type,
                effective_backend,
                level,
                &id,
                &project_dir,
            )
            .or_else(|| {
                eprintln!(
                    "lince-dashboard: sandbox_level={} not yet supported for agent_type={} — using static command",
                    level, agent_type
                );
                None
            })
        });
        if let Some(argv) = synthesized {
            expanded.extend(argv);
        } else {
            expanded.extend(expand_command_template(
                &type_config.command,
                &id,
                &project_dir,
                profile.as_deref(),
            ));
        }
        // For agent-sandbox (bwrap) agents, pass the profile via -P flag so
        // agent-sandbox can resolve the profile's env vars internally.
        // Nono agents already have --profile baked into their command template.
        if type_config.sandboxed && *effective_backend == SandboxBackend::AgentSandbox {
            if let Some(ref p) = profile {
                if !p.is_empty() {
                    expanded.push("-P".to_string());
                    expanded.push(p.clone());
                }
            }
        }
        expanded
    } else {
        // Legacy fallback: use sandbox_command (backward compat when agent_types not loaded)
        let mut args: Vec<String> = vec![
            format!("LINCE_AGENT_ID={}", id),
            config.sandbox_command.clone(),
            "run".to_string(),
        ];
        if let Some(ref p) = profile {
            if !p.is_empty() {
                args.push("-P".to_string());
                args.push(p.clone());
            }
        }
        args.push("-p".to_string());
        args.push(project_dir.clone());
        args
    };

    let command = CommandToRun {
        path: PathBuf::from("/usr/bin/env"),
        args,
        cwd: Some(PathBuf::from(&project_dir)),
    };

    match config.agent_layout {
        AgentLayout::Floating => {
            open_command_pane_floating(command, Some(default_agent_pane_coords()), BTreeMap::new());
        }
        AgentLayout::Tiled => {
            open_command_pane(command, BTreeMap::new());
        }
    }

    let started_at = now_secs();

    // Resolve the effective sandbox level to store on AgentInfo for color-coding and save/restore.
    let resolved_sandbox_level = sandbox_level_override
        .or_else(|| config.agent_types.get(agent_type).and_then(|c| c.sandbox_level.clone()));
    // Resolved backend for save/restore + dashboard table label override.
    let resolved_sandbox_backend = sandbox_backend_override
        .or_else(|| config.agent_types.get(agent_type).map(|c| c.sandbox_backend.clone()));

    Ok(AgentInfo {
        id,
        name,
        agent_type: agent_type.to_string(),
        profile,
        project_dir,
        status: AgentStatus::Starting,
        pane_id: None,
        tokens_in: 0,
        tokens_out: 0,
        current_tool: None,
        started_at: if started_at > 0 { Some(started_at) } else { None },
        last_error: None,
        exit_code: None,
        group,
        running_subagents: 0,
        model: None,
        last_polled_event: None,
        sandbox_level: resolved_sandbox_level,
        sandbox_backend: resolved_sandbox_backend,
    })
}

/// Spawn a new agent with custom name, profile, project directory, and optional sandbox overrides.
///
/// `sandbox_level_override` / `sandbox_backend_override` are the runtime values selected in the
/// wizard (or restored from saved state). When `None`, `spawn_inner` falls back to the
/// TOML-pinned values for the agent type.
pub fn spawn_agent_custom(
    config: &DashboardConfig,
    next_id: &mut u32,
    agents: &[AgentInfo],
    custom_name: String,
    agent_type: &str,
    custom_profile: Option<String>,
    custom_project_dir: String,
    launch_dir: Option<&str>,
    sandbox_level_override: Option<String>,
    sandbox_backend_override: Option<SandboxBackend>,
) -> Result<AgentInfo, String> {
    let profile = match custom_profile {
        Some(ref p) if p.is_empty() => None,
        other => other,
    };
    let project_dir = if custom_project_dir.is_empty() {
        launch_dir.unwrap_or(".").to_string()
    } else {
        // The wizard UI may collapse $HOME to ~, but PathBuf treats ~ as literal.
        crate::config::expand_tilde(&custom_project_dir)
    };

    spawn_inner(
        config,
        next_id,
        agents,
        custom_name,
        agent_type,
        profile,
        project_dir,
        None,
        sandbox_level_override,
        sandbox_backend_override,
    )
}

/// Stop an agent by closing its pane.
pub fn stop_agent(agent: &AgentInfo) {
    if let Some(pid) = agent.pane_id {
        close_terminal_pane(pid);
    }
}

/// Update agent pane tracking based on PaneManifest from a PaneUpdate event.
/// Returns true if any agent state changed (to avoid unnecessary re-renders).
/// Uses per-agent-type `pane_title_pattern` from config for pane matching.
pub fn reconcile_panes(
    agents: &mut Vec<AgentInfo>,
    manifest: &PaneManifest,
    agent_layout: &AgentLayout,
    agent_types: &HashMap<String, AgentTypeConfig>,
) -> bool {
    let mut changed = false;

    let mut all_panes: Vec<&PaneInfo> = Vec::new();
    for panes in manifest.panes.values() {
        for pane in panes {
            if !pane.is_plugin {
                all_panes.push(pane);
            }
        }
    }

    use std::collections::HashSet;

    let all_pane_ids: HashSet<u32> = all_panes.iter().map(|p| p.id).collect();
    let mut assigned_ids: HashSet<u32> = agents.iter().filter_map(|a| a.pane_id).collect();
    let expect_floating = !agent_layout.is_tiled();

    for agent in agents.iter_mut() {
        if let Some(pid) = agent.pane_id {
            if !all_pane_ids.contains(&pid) {
                agent.status = AgentStatus::Stopped;
                agent.pane_id = None;
                agent.exit_code = None;
                changed = true;
            } else if let Some(pane) = all_panes.iter().find(|p| p.id == pid) {
                if pane.exited && agent.status != AgentStatus::Stopped {
                    agent.exit_code = pane.exit_status;
                    agent.last_error = pane.exit_status.filter(|&c| c != 0).map(|c| format!("Process exited with code {c}"));
                    agent.status = AgentStatus::Stopped;
                    changed = true;
                }
            }
        } else if agent.status == AgentStatus::Starting {
            // Resolve pane title patterns for this agent's type. For sandboxed
            // agents the actual title varies by backend (agent-sandbox / nono /
            // bash wrapper), so we accept any of: the TOML-configured pattern,
            // "nono" (for nono backend), and the agent's base name (e.g. "claude"
            // — the inner command Zellij ends up showing for some launchers).
            // Unsandboxed agents only match the TOML pattern (usually the binary name).
            let cfg = agent_types.get(&agent.agent_type);
            let primary_pattern = cfg
                .map(|c| c.pane_title_pattern.as_str())
                .unwrap_or(DEFAULT_SANDBOX_COMMAND);
            let base = agent_type_base_name(&agent.agent_type);
            let sandboxed = cfg.map_or(true, |c| c.sandboxed);
            let patterns: Vec<&str> = if sandboxed {
                vec![primary_pattern, "nono", base]
            } else {
                vec![primary_pattern]
            };
            for pane in &all_panes {
                if pane.is_floating == expect_floating
                    && !pane.is_suppressed
                    && !pane.exited
                    && !assigned_ids.contains(&pane.id)
                    && patterns.iter().any(|p| pane.title.contains(p))
                {
                    agent.pane_id = Some(pane.id);
                    assigned_ids.insert(pane.id);
                    agent.status = AgentStatus::WaitingForInput;
                    let title = pane_title(&agent.name, &agent.agent_type, agent_types, agent.sandbox_level.as_deref());
                    rename_pane_with_id(PaneId::Terminal(pane.id), &title);
                    if expect_floating {
                        hide_pane_with_id(PaneId::Terminal(pane.id));
                    }
                    changed = true;
                    break;
                }
            }
        }
    }

    // NOTE: We intentionally do NOT auto-remove stopped agents here.
    // Previously, agents whose panes exited were silently removed, which
    // caused restored agents to "disappear" if their pane command failed
    // before the user could see them.  Stopped agents now stay in the list
    // with a "Stopped" status until the user manually removes them with [x].

    changed
}
