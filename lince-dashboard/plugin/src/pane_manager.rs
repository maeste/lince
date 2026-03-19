use zellij_tile::prelude::*;

use crate::config::FocusMode;
use crate::types::AgentInfo;

/// Show and focus the given agent's pane, hiding all other agent panes.
pub fn focus_agent(agent: &AgentInfo, all_agents: &[AgentInfo], focus_mode: &FocusMode) -> bool {
    let pid = match agent.pane_id {
        Some(pid) => pid,
        None => return false,
    };

    // Hide all OTHER agent floating panes first
    for other in all_agents {
        if other.id != agent.id {
            if let Some(other_pid) = other.pane_id {
                hide_pane_with_id(PaneId::Terminal(other_pid));
            }
        }
    }

    match focus_mode {
        FocusMode::Floating => {
            show_pane_with_id(PaneId::Terminal(pid), true);
            focus_terminal_pane(pid, true);
            // Resize to 80% x 85%, centered
            let coords = FloatingPaneCoordinates::default()
                .with_x_percent(10)
                .with_y_percent(5)
                .with_width_percent(80)
                .with_height_percent(85);
            change_floating_panes_coordinates(vec![(PaneId::Terminal(pid), coords)]);
        }
        FocusMode::Replace => {
            focus_terminal_pane(pid, false);
        }
    }
    true
}

/// Hide the given agent's pane and return focus to the dashboard.
pub fn unfocus_agent(
    agent: &AgentInfo,
    focus_mode: &FocusMode,
    dashboard_tab_index: Option<u32>,
) {
    if let Some(pid) = agent.pane_id {
        match focus_mode {
            FocusMode::Floating => {
                hide_pane_with_id(PaneId::Terminal(pid));
            }
            FocusMode::Replace => {
                if let Some(tab_idx) = dashboard_tab_index {
                    go_to_tab(tab_idx);
                }
            }
        }
    }
}

/// Focus the next agent in the list (with wrap-around), showing its pane.
pub fn focus_next(
    agents: &[AgentInfo],
    current_index: usize,
    focus_mode: &FocusMode,
) -> Option<usize> {
    if agents.is_empty() {
        return None;
    }
    let next = (current_index + 1) % agents.len();
    if focus_agent(&agents[next], agents, focus_mode) {
        Some(next)
    } else {
        None
    }
}

/// Focus the previous agent in the list (with wrap-around), showing its pane.
pub fn focus_prev(
    agents: &[AgentInfo],
    current_index: usize,
    focus_mode: &FocusMode,
) -> Option<usize> {
    if agents.is_empty() {
        return None;
    }
    let prev = if current_index == 0 {
        agents.len() - 1
    } else {
        current_index - 1
    };
    if focus_agent(&agents[prev], agents, focus_mode) {
        Some(prev)
    } else {
        None
    }
}
