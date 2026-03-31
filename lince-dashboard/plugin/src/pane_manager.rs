use zellij_tile::prelude::*;

use crate::config::{AgentLayout, FocusMode};
use crate::types::AgentInfo;

/// Hide agent floating panes. If `except` is provided, skip that agent.
/// No-op when `agent_layout` is `Tiled` (tiled panes should stay visible).
pub fn hide_agent_panes(agents: &[AgentInfo], except: Option<&str>, agent_layout: &AgentLayout) {
    if agent_layout.is_tiled() {
        return;
    }
    for agent in agents {
        if except.map_or(false, |id| agent.id == id) {
            continue;
        }
        if let Some(pid) = agent.pane_id {
            hide_pane_with_id(PaneId::Terminal(pid));
        }
    }
}

/// Show and focus the given agent's pane, hiding all other agent panes.
pub fn focus_agent(
    agent: &AgentInfo,
    all_agents: &[AgentInfo],
    focus_mode: &FocusMode,
    agent_layout: &AgentLayout,
) -> bool {
    let pid = match agent.pane_id {
        Some(pid) => pid,
        None => return false,
    };

    if agent_layout.is_tiled() {
        // Tiled panes are always visible — just switch terminal focus.
        focus_terminal_pane(pid, false, true);
    } else {
        hide_agent_panes(all_agents, Some(&agent.id), agent_layout);

        match focus_mode {
            FocusMode::Floating => {
                show_pane_with_id(PaneId::Terminal(pid), true, true);
                focus_terminal_pane(pid, true, true);
                change_floating_panes_coordinates(vec![
                    (PaneId::Terminal(pid), crate::agent::default_agent_pane_coords()),
                ]);
            }
            FocusMode::Replace => {
                focus_terminal_pane(pid, false, true);
            }
        }
    }
    true
}

/// Hide the given agent's pane and return focus to the dashboard.
pub fn unfocus_agent(agent: &AgentInfo, focus_mode: &FocusMode, agent_layout: &AgentLayout) {
    if agent_layout.is_tiled() {
        // Tiled panes stay visible; the dashboard plugin pane regains focus
        // when the user navigates back (e.g. via Zellij keybinding).
        return;
    }
    if let Some(pid) = agent.pane_id {
        match focus_mode {
            FocusMode::Floating => {
                hide_pane_with_id(PaneId::Terminal(pid));
            }
            FocusMode::Replace => {
                // In replace mode, hiding isn't needed — the dashboard tab
                // regains focus automatically when the plugin re-renders.
            }
        }
    }
}

/// Focus the next agent in the list (with wrap-around), showing its pane.
pub fn focus_next(
    agents: &[AgentInfo],
    current_index: usize,
    focus_mode: &FocusMode,
    agent_layout: &AgentLayout,
) -> Option<usize> {
    if agents.is_empty() {
        return None;
    }
    let next = (current_index + 1) % agents.len();
    if focus_agent(&agents[next], agents, focus_mode, agent_layout) {
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
    agent_layout: &AgentLayout,
) -> Option<usize> {
    if agents.is_empty() {
        return None;
    }
    let prev = if current_index == 0 {
        agents.len() - 1
    } else {
        current_index - 1
    };
    if focus_agent(&agents[prev], agents, focus_mode, agent_layout) {
        Some(prev)
    } else {
        None
    }
}
