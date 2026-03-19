mod agent;
mod config;
mod dashboard;
mod pane_manager;
mod types;

use std::collections::BTreeMap;
use zellij_tile::prelude::*;

use crate::config::{DashboardConfig, StatusMethod};
use crate::types::{AgentInfo, StatusMessage};

struct State {
    rows: usize,
    cols: usize,
    config: DashboardConfig,
    config_error: Option<String>,
    agents: Vec<AgentInfo>,
    selected_index: usize,
    focused_agent: Option<String>,
    input_mode: bool,
    status_message: Option<String>,
    next_agent_id: u32,
}

impl Default for State {
    fn default() -> Self {
        Self {
            rows: 0,
            cols: 0,
            config: DashboardConfig::default(),
            config_error: None,
            agents: Vec::new(),
            selected_index: 0,
            focused_agent: None,
            input_mode: false,
            status_message: None,
            next_agent_id: 0,
        }
    }
}

register_plugin!(State);

impl ZellijPlugin for State {
    fn load(&mut self, configuration: BTreeMap<String, String>) {
        if let Some(path) = configuration.get("config_path") {
            let (cfg, err) = DashboardConfig::load(path);
            self.config = cfg;
            self.config_error = err;
        }
        subscribe(&[
            EventType::Key,
            EventType::Timer,
            EventType::PaneUpdate,
            EventType::ModeUpdate,
            EventType::RunCommandResult,
            EventType::PermissionRequestResult,
        ]);
        request_permission(&[
            PermissionType::RunCommands,
            PermissionType::ChangeApplicationState,
            PermissionType::ReadApplicationState,
            PermissionType::MessageAndLaunchOtherPlugins,
            PermissionType::OpenTerminalsOrPlugins,
        ]);

        // Start file-polling timer if using file-based status detection
        if self.config.status_method == StatusMethod::File {
            set_timeout(2.0);
        }
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => true,
            Event::Key(key) => self.handle_key(key),
            Event::PaneUpdate(manifest) => {
                agent::reconcile_panes(&mut self.agents, &manifest);
                true
            }
            Event::Timer(_elapsed) => {
                // File-based status polling fallback
                if self.config.status_method == StatusMethod::File {
                    self.poll_status_files();
                    set_timeout(2.0);
                    return true;
                }
                // Clear transient status messages after timeout
                if self.status_message.is_some() && self.config_error.is_none() {
                    self.status_message = None;
                    return true;
                }
                false
            }
            _ => false,
        }
    }

    fn render(&mut self, rows: usize, cols: usize) {
        self.rows = rows;
        self.cols = cols;

        let config_warning = self.config_error.as_deref();
        let effective_status = self.status_message.as_deref().or(config_warning);

        dashboard::render_dashboard(
            &self.agents,
            self.selected_index,
            self.focused_agent.as_deref(),
            rows,
            cols,
            self.input_mode,
            effective_status,
        );
    }

    fn pipe(&mut self, pipe_message: PipeMessage) -> bool {
        match pipe_message.name.as_str() {
            "claude-status" => {
                if let Some(payload) = pipe_message.payload {
                    self.handle_status_message(&payload);
                    return true;
                }
                false
            }
            "voxcode-text" => {
                if let Some(payload) = pipe_message.payload {
                    self.handle_voxcode_text(&payload);
                    return true;
                }
                false
            }
            _ => false,
        }
    }
}

impl State {
    fn handle_key(&mut self, key: KeyWithModifier) -> bool {
        let bare = &key.bare_key;
        let no_mods = key.key_modifiers.is_empty();

        // In input mode, all keys except Escape are forwarded to the agent
        if self.input_mode {
            if no_mods && *bare == BareKey::Esc {
                self.input_mode = false;
                self.status_message = None;
                return true;
            }
            // Forward char to focused/selected agent
            if let Some(agent) = self.agents.get(self.selected_index) {
                if let Some(pid) = agent.pane_id {
                    if let BareKey::Char(c) = bare {
                        write_chars_to_pane_id(
                            &c.to_string(),
                            PaneId::Terminal(pid),
                        );
                    }
                }
            }
            return false;
        }

        if !no_mods {
            return false;
        }

        match bare {
            BareKey::Char('n') => {
                match agent::spawn_agent(
                    &self.config,
                    &mut self.next_agent_id,
                    &self.agents,
                ) {
                    Ok(info) => {
                        self.status_message =
                            Some(format!("Spawned {}", info.name));
                        self.agents.push(info);
                        self.selected_index = self.agents.len().saturating_sub(1);
                    }
                    Err(e) => {
                        self.status_message = Some(e);
                    }
                }
                true
            }
            BareKey::Char('k') => {
                if let Some(agent) = self.agents.get(self.selected_index) {
                    let name = agent.name.clone();
                    agent::stop_agent(agent);
                    self.agents.remove(self.selected_index);
                    if self.selected_index > 0 && self.selected_index >= self.agents.len() {
                        self.selected_index = self.agents.len().saturating_sub(1);
                    }
                    self.status_message = Some(format!("Killed {}", name));
                }
                true
            }
            BareKey::Char('j') | BareKey::Down => {
                if !self.agents.is_empty() {
                    self.selected_index = (self.selected_index + 1) % self.agents.len();
                }
                true
            }
            BareKey::Up => {
                if !self.agents.is_empty() {
                    if self.selected_index == 0 {
                        self.selected_index = self.agents.len() - 1;
                    } else {
                        self.selected_index -= 1;
                    }
                }
                true
            }
            BareKey::Char('f') | BareKey::Enter => {
                if let Some(agent) = self.agents.get(self.selected_index) {
                    if pane_manager::focus_agent(agent, &self.agents, &self.config.focus_mode) {
                        self.focused_agent = Some(agent.id.clone());
                        self.status_message = Some(format!("Focused {}", agent.name));
                    }
                }
                true
            }
            BareKey::Char('h') | BareKey::Esc => {
                // Unfocus (hide) the currently focused agent
                if let Some(ref focused_id) = self.focused_agent.clone() {
                    if let Some(agent) = self.agents.iter().find(|a| &a.id == focused_id) {
                        pane_manager::unfocus_agent(agent, &self.config.focus_mode, None);
                    }
                    self.focused_agent = None;
                    self.status_message = None;
                }
                true
            }
            BareKey::Char(']') => {
                // Focus next agent directly
                if let Some(ref focused_id) = self.focused_agent.clone() {
                    // Unfocus current
                    if let Some(agent) = self.agents.iter().find(|a| &a.id == focused_id) {
                        pane_manager::unfocus_agent(agent, &self.config.focus_mode, None);
                    }
                }
                if let Some(new_idx) = pane_manager::focus_next(
                    &self.agents,
                    self.selected_index,
                    &self.config.focus_mode,
                ) {
                    self.selected_index = new_idx;
                    self.focused_agent = Some(self.agents[new_idx].id.clone());
                }
                true
            }
            BareKey::Char('[') => {
                // Focus previous agent directly
                if let Some(ref focused_id) = self.focused_agent.clone() {
                    if let Some(agent) = self.agents.iter().find(|a| &a.id == focused_id) {
                        pane_manager::unfocus_agent(agent, &self.config.focus_mode, None);
                    }
                }
                if let Some(new_idx) = pane_manager::focus_prev(
                    &self.agents,
                    self.selected_index,
                    &self.config.focus_mode,
                ) {
                    self.selected_index = new_idx;
                    self.focused_agent = Some(self.agents[new_idx].id.clone());
                }
                true
            }
            BareKey::Char('i') => {
                if self.agents.get(self.selected_index).is_some() {
                    self.input_mode = true;
                    self.status_message = None;
                }
                true
            }
            _ => false,
        }
    }

    /// Handle a "claude-status" pipe message (LINCE-42).
    fn handle_status_message(&mut self, payload: &str) {
        let msg: StatusMessage = match serde_json::from_str(payload) {
            Ok(m) => m,
            Err(_) => return, // silently ignore malformed messages
        };
        let new_status = msg.to_agent_status();
        if let Some(agent) = self.agents.iter_mut().find(|a| a.id == msg.agent_id) {
            agent.status = new_status;
        }
    }

    /// Handle a "voxcode-text" pipe message — relay text to active agent (LINCE-43).
    fn handle_voxcode_text(&mut self, text: &str) {
        // Find the target agent: focused > selected > none
        let target_pane_id = if let Some(ref focused_id) = self.focused_agent {
            self.agents
                .iter()
                .find(|a| &a.id == focused_id)
                .and_then(|a| a.pane_id)
        } else {
            self.agents
                .get(self.selected_index)
                .and_then(|a| a.pane_id)
        };

        match target_pane_id {
            Some(pid) => {
                write_chars_to_pane_id(text, PaneId::Terminal(pid));
            }
            None => {
                self.status_message =
                    Some("No agent to receive text".to_string());
                // Auto-clear after 3 seconds
                set_timeout(3.0);
            }
        }
    }

    /// Poll status files for all agents (file-based fallback, LINCE-42).
    fn poll_status_files(&mut self) {
        let status_dir = &self.config.status_file_dir;
        for agent in self.agents.iter_mut() {
            let path = format!("{}/claude-{}.state", status_dir, agent.id);
            if let Ok(content) = std::fs::read_to_string(&path) {
                let event = content.trim().to_string();
                if !event.is_empty() {
                    let msg = StatusMessage {
                        agent_id: agent.id.clone(),
                        event,
                        timestamp: None,
                    };
                    agent.status = msg.to_agent_status();
                }
            }
        }
    }
}
