use std::collections::BTreeMap;
use std::path::PathBuf;

use zellij_tile::prelude::*;

use crate::config::DashboardConfig;
use crate::types::{AgentInfo, AgentStatus};

/// Spawn a new agent as a floating command pane running claude-sandbox.
/// Returns the AgentInfo (with pane_id = None until PaneUpdate confirms it).
pub fn spawn_agent(
    config: &DashboardConfig,
    next_id: &mut u32,
    agents: &[AgentInfo],
) -> Result<AgentInfo, String> {
    if agents.len() >= config.max_agents {
        return Err(format!(
            "Max agents reached ({}). Kill one first.",
            config.max_agents
        ));
    }

    *next_id += 1;
    let id = format!("agent-{}", next_id);
    let name = id.clone();

    let profile = config.default_profile.clone();
    let project_dir = config
        .default_project_dir
        .clone()
        .unwrap_or_else(|| ".".to_string());

    // Use `env` to set LINCE_AGENT_ID as an environment variable for the process.
    // The context BTreeMap is pane metadata, NOT env vars — so we wrap with `env`.
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

    let context = BTreeMap::new();

    // Open as a floating pane with large size (80% x 85%, centered)
    let coords = FloatingPaneCoordinates::default()
        .with_x_percent(10)
        .with_y_percent(5)
        .with_width_percent(80)
        .with_height_percent(85);
    open_command_pane_floating(command, Some(coords), context);

    // Note: We cannot get the pane_id synchronously. It will be resolved
    // when we receive a PaneUpdate event and match by title/command.

    Ok(AgentInfo {
        id,
        name,
        profile,
        project_dir,
        status: AgentStatus::Starting,
        pane_id: None,
        pane_ids: Vec::new(),
    })
}

/// Stop an agent by closing its pane(s).
pub fn stop_agent(agent: &AgentInfo) {
    if let Some(pid) = agent.pane_id {
        close_terminal_pane(pid);
    }
    for &pid in &agent.pane_ids {
        close_terminal_pane(pid);
    }
}

/// Update agent pane tracking based on PaneManifest from a PaneUpdate event.
/// Assigns pane_ids to agents that don't have them yet (matching by command),
/// and marks agents whose panes have disappeared as Stopped.
pub fn reconcile_panes(agents: &mut Vec<AgentInfo>, manifest: &PaneManifest) {
    // Collect all terminal pane IDs and their info across all tabs
    let mut all_panes: Vec<&PaneInfo> = Vec::new();
    for panes in manifest.panes.values() {
        for pane in panes {
            if !pane.is_plugin {
                all_panes.push(pane);
            }
        }
    }

    let all_pane_ids: Vec<u32> = all_panes.iter().map(|p| p.id).collect();

    // Collect already-assigned pane IDs before the mutable loop
    let assigned_ids: Vec<u32> = agents.iter().filter_map(|a| a.pane_id).collect();

    for agent in agents.iter_mut() {
        if let Some(pid) = agent.pane_id {
            // Check if the pane still exists
            if !all_pane_ids.contains(&pid) {
                agent.status = AgentStatus::Stopped;
                agent.pane_id = None;
            } else {
                // Check if it exited
                if let Some(pane) = all_panes.iter().find(|p| p.id == pid) {
                    if pane.exited {
                        agent.status = AgentStatus::Stopped;
                    }
                }
            }
        } else if agent.status == AgentStatus::Starting {
            // Try to find a matching pane for this starting agent.
            // We look for a non-plugin, floating pane that contains
            // "claude-sandbox" in its title and isn't already assigned.
            for pane in &all_panes {
                if pane.is_floating
                    && !pane.is_suppressed
                    && !assigned_ids.contains(&pane.id)
                    && pane.title.contains("claude-sandbox")
                {
                    agent.pane_id = Some(pane.id);
                    agent.status = AgentStatus::WaitingForInput;
                    // Set pane title to agent name for identification
                    rename_pane_with_id(PaneId::Terminal(pane.id), &agent.name);
                    // Hide it immediately — agents are hidden by default
                    hide_pane_with_id(PaneId::Terminal(pane.id));
                    break;
                }
            }
        }
    }

    // Remove agents that have been stopped for a while (pane gone)
    agents.retain(|a| {
        if a.status == AgentStatus::Stopped && a.pane_id.is_none() {
            false
        } else {
            true
        }
    });
}
