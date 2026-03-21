use std::collections::BTreeMap;
use std::path::PathBuf;

use zellij_tile::prelude::*;

use crate::config::{AgentLayout, DashboardConfig};
use crate::types::{AgentInfo, AgentStatus};

/// Default floating pane coordinates for agent panes (80% x 85%, centered).
pub fn default_agent_pane_coords() -> FloatingPaneCoordinates {
    FloatingPaneCoordinates::default()
        .with_x_percent(20)
        .with_y_percent(5)
        .with_width_percent(80)
        .with_height_percent(85)
}

/// Get current Unix timestamp in seconds, or 0 if unavailable (e.g. WASM).
fn current_timestamp_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Internal helper that does the actual spawn work.
/// All public spawn functions resolve their parameters and delegate here.
fn spawn_inner(
    config: &DashboardConfig,
    next_id: &mut u32,
    agents: &[AgentInfo],
    name: String,
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
    let id = format!("agent-{}", next_id);
    let name = if name.is_empty() { id.clone() } else { name };

    // Build command args: env LINCE_AGENT_ID=... sandbox run [-P profile] -p dir
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

    let started_at = current_timestamp_secs();

    Ok(AgentInfo {
        id,
        name,
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
    })
}

/// Spawn a new agent with custom name, profile, and project directory.
pub fn spawn_agent_custom(
    config: &DashboardConfig,
    next_id: &mut u32,
    agents: &[AgentInfo],
    custom_name: String,
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

    spawn_inner(config, next_id, agents, custom_name, profile, project_dir, None)
}

/// Stop an agent by closing its pane.
pub fn stop_agent(agent: &AgentInfo) {
    if let Some(pid) = agent.pane_id {
        close_terminal_pane(pid);
    }
}

/// Update agent pane tracking based on PaneManifest from a PaneUpdate event.
/// Returns true if any agent state changed (to avoid unnecessary re-renders).
pub fn reconcile_panes(
    agents: &mut Vec<AgentInfo>,
    manifest: &PaneManifest,
    agent_layout: &AgentLayout,
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
            for pane in &all_panes {
                if pane.is_floating == expect_floating
                    && !pane.is_suppressed
                    && !pane.exited
                    && !assigned_ids.contains(&pane.id)
                    && pane.title.contains("claude-sandbox")
                {
                    agent.pane_id = Some(pane.id);
                    assigned_ids.insert(pane.id);
                    agent.status = AgentStatus::WaitingForInput;
                    rename_pane_with_id(PaneId::Terminal(pane.id), &agent.name);
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
