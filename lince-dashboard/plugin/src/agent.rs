use std::collections::{BTreeMap, HashMap};
use std::path::PathBuf;

use zellij_tile::prelude::*;

use crate::config::{AgentLayout, AgentTypeConfig, DashboardConfig, DEFAULT_SANDBOX_COMMAND};
use crate::sandbox_backend::SandboxBackend;

/// Name of the lifecycle wrapper script for agents without native hooks.
const AGENT_WRAPPER: &str = "lince-agent-wrapper";
use crate::types::{AgentInfo, AgentStatus};

/// Variant suffixes stripped by `agent_type_base_name()`.
/// Add new suffixes here when new sandbox variants are introduced.
const AGENT_TYPE_SUFFIXES: &[&str] = &["-unsandboxed", "-bwrap", "-nono"];

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

/// Build pane title, prefixing with `[UNSANDBOXED]` for non-sandboxed agent types.
pub fn pane_title(name: &str, agent_type: &str, agent_types: &HashMap<String, AgentTypeConfig>) -> String {
    let sandboxed = agent_types.get(agent_type).map_or(true, |c| c.sandboxed);
    if sandboxed {
        name.to_string()
    } else {
        format!("[NON-SANDBOXED] {}", name)
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
        expanded.extend(expand_command_template(
            &type_config.command,
            &id,
            &project_dir,
            profile.as_deref(),
        ));
        // For agent-sandbox (bwrap) agents, pass the profile via -P flag so
        // agent-sandbox can resolve the profile's env vars internally.
        // Nono agents already have --profile baked into their command template.
        if type_config.sandboxed && type_config.sandbox_backend == SandboxBackend::AgentSandbox {
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
        group,
        running_subagents: 0,
        model: None,
        last_polled_event: None,
    })
}

/// Spawn a new agent with custom name, profile, and project directory.
pub fn spawn_agent_custom(
    config: &DashboardConfig,
    next_id: &mut u32,
    agents: &[AgentInfo],
    custom_name: String,
    agent_type: &str,
    custom_profile: Option<String>,
    custom_project_dir: String,
    launch_dir: Option<&str>,
) -> Result<AgentInfo, String> {
    let profile = match custom_profile {
        Some(ref p) if p.is_empty() => None,
        other => other,
    };
    let project_dir = if custom_project_dir.is_empty() {
        launch_dir.unwrap_or(".").to_string()
    } else {
        custom_project_dir
    };

    spawn_inner(config, next_id, agents, custom_name, agent_type, profile, project_dir, None)
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
                changed = true;
            } else if let Some(pane) = all_panes.iter().find(|p| p.id == pid) {
                if pane.exited && agent.status != AgentStatus::Stopped {
                    agent.status = AgentStatus::Stopped;
                    changed = true;
                }
            }
        } else if agent.status == AgentStatus::Starting {
            // Resolve the pane title pattern for this agent's type.
            // Falls back to "agent-sandbox" if the agent type is not in config.
            let pattern = agent_types
                .get(&agent.agent_type)
                .map(|c| c.pane_title_pattern.as_str())
                .unwrap_or(DEFAULT_SANDBOX_COMMAND);
            for pane in &all_panes {
                if pane.is_floating == expect_floating
                    && !pane.is_suppressed
                    && !pane.exited
                    && !assigned_ids.contains(&pane.id)
                    && pane.title.contains(pattern)
                {
                    agent.pane_id = Some(pane.id);
                    assigned_ids.insert(pane.id);
                    agent.status = AgentStatus::WaitingForInput;
                    let title = pane_title(&agent.name, &agent.agent_type, agent_types);
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
