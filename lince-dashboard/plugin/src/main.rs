mod agent;
mod config;
mod dashboard;
mod pane_manager;
mod sandbox_backend;
mod state_file;
mod types;

use std::collections::BTreeMap;
use zellij_tile::prelude::*;

use crate::config::{DashboardConfig, StatusMethod, DEFAULT_AGENT_TYPE};
use crate::sandbox_backend::DetectedBackends;

const PIPE_CLAUDE_STATUS: &str = "claude-status";
const PIPE_LINCE_STATUS: &str = "lince-status";
const PIPE_VOXCODE_TEXT: &str = "voxcode-text";
const CMD_GET_CWD: &str = "get_cwd";

use crate::types::{
    AgentInfo, AgentStatus, NamePromptState, SavedAgentInfo,
    StatusMessage, WizardState, WizardStep,
};

struct State {
    config: DashboardConfig,
    config_error: Option<String>,
    config_path: Option<String>,
    config_mtime: u64,
    agents: Vec<AgentInfo>,
    selected_index: usize,
    focused_agent: Option<String>,
    show_detail: bool,
    show_help: bool,
    status_message: Option<String>,
    next_agent_id: u32,
    wizard: Option<WizardState>,
    name_prompt: Option<NamePromptState>,
    /// When set, the name_prompt acts as a rename prompt for this agent id.
    rename_target: Option<String>,
    launch_dir: Option<String>,
    /// Buffered saved state awaiting agent type defaults before restore.
    /// Set when load_state completes before load_agent_defaults.
    pending_restore: Option<Vec<SavedAgentInfo>>,
    /// Whether agent type defaults have been loaded at least once.
    agent_types_loaded: bool,
    /// Detected sandbox backends (populated async after permissions granted).
    detected_backends: Option<DetectedBackends>,
}

impl Default for State {
    fn default() -> Self {
        Self {
            config: DashboardConfig::default(),
            config_error: None,
            config_path: None,
            config_mtime: 0,
            agents: Vec::new(),
            selected_index: 0,
            focused_agent: None,
            show_detail: true,
            show_help: false,
            status_message: None,
            next_agent_id: 0,
            wizard: None,
            name_prompt: None,
            rename_target: None,
            launch_dir: None,
            pending_restore: None,
            agent_types_loaded: false,
            detected_backends: None,
        }
    }
}

/// Wrap-around list navigation helper.
fn wrap_next(current: usize, len: usize) -> usize {
    if len == 0 { 0 } else { (current + 1) % len }
}

fn wrap_prev(current: usize, len: usize) -> usize {
    if len == 0 { 0 } else if current == 0 { len - 1 } else { current - 1 }
}

register_plugin!(State);

impl ZellijPlugin for State {
    fn load(&mut self, configuration: BTreeMap<String, String>) {
        if let Some(raw_path) = configuration.get("config_path") {
            let path = config::expand_tilde(raw_path);
            let (cfg, err) = DashboardConfig::load(&path);
            self.config = cfg;
            self.config_error = err;
            self.config_mtime = config::get_file_mtime(&path);
            self.config_path = Some(path);
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
            PermissionType::ReadCliPipes,
            PermissionType::WriteToStdin,
        ]);

        // Always start timer: serves both file-polling and config hot-reload
        set_timeout(5.0);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                // Now that we have permissions, detect CWD via `pwd`.
                config::run_typed_command(&["pwd"], CMD_GET_CWD);
                // Detect available sandbox backends (agent-sandbox, nono).
                sandbox_backend::detect_backend_async();
                true
            }
            Event::Key(key) => self.handle_key(key),
            Event::PaneUpdate(manifest) => {
                let changed = agent::reconcile_panes(&mut self.agents, &manifest, &self.config.agent_layout, &self.config.agent_types);
                if changed {
                    self.sort_agents_by_dir();
                }
                changed
            }
            Event::Timer(_elapsed) => {
                let mut needs_render = false;

                // Config hot-reload check
                if let Some(ref path) = self.config_path {
                    let new_mtime = config::get_file_mtime(path);
                    if new_mtime != self.config_mtime && new_mtime > 0 {
                        self.config_mtime = new_mtime;
                        let p = path.clone(); // clone only when reload needed
                        self.reload_config(&p);
                        needs_render = true;
                    }
                }

                // File-based status polling fallback
                if self.config.status_method == StatusMethod::File {
                    if self.poll_status_files() {
                        needs_render = true;
                    }
                }

                // Clear transient status messages after timeout
                if self.status_message.is_some() && self.config_error.is_none() {
                    self.status_message = None;
                    needs_render = true;
                }

                set_timeout(5.0); // re-arm for config reload + polling
                needs_render
            }
            Event::RunCommandResult(exit_code, stdout, stderr, context) => {
                let cmd_type = context.get(config::CMD_TYPE_KEY).map(|s| s.as_str());
                match cmd_type {
                    Some(CMD_GET_CWD) if exit_code == Some(0) => {
                        let dir = String::from_utf8_lossy(&stdout).trim().to_string();
                        if !dir.is_empty() {
                            // Kick off async profile discovery (reads sandbox config via shell).
                            config::discover_profiles_async(
                                self.config.sandbox_config_path.as_deref(),
                                Some(&dir),
                            );
                            // Kick off async load of agent type defaults.
                            config::load_agent_defaults_async(
                                self.config.sandbox_config_path.as_deref(),
                            );
                            // Kick off async load of saved state.
                            state_file::load_state_async(&dir);
                            self.launch_dir = Some(dir);
                        }
                        true
                    }
                    Some(state_file::CMD_LOAD_STATE) => {
                        if exit_code == Some(0) && !stdout.is_empty() {
                            match state_file::parse_loaded_state(&stdout) {
                                Ok(saved) => {
                                    self.next_agent_id = saved.next_agent_id;
                                    if self.agent_types_loaded {
                                        // Agent types already available — restore immediately.
                                        self.restore_agents(saved.agents);
                                    } else {
                                        // Agent types not loaded yet — buffer for later.
                                        self.pending_restore = Some(saved.agents);
                                    }
                                }
                                Err(e) => {
                                    self.status_message = Some(format!("Restore: {}", e));
                                    set_timeout(5.0);
                                }
                            }
                        }
                        // exit_code != 0 means file not found — normal, ignore.
                        true
                    }
                    Some(state_file::CMD_SAVE_STATE) => {
                        if exit_code == Some(0) {
                            quit_zellij();
                        } else {
                            let err = String::from_utf8_lossy(&stderr);
                            self.status_message = Some(format!("Save failed: {}", err.trim()));
                            set_timeout(5.0);
                        }
                        true
                    }
                    Some(state_file::CMD_DELETE_STATE) => {
                        // Nothing to do, just acknowledge.
                        false
                    }
                    Some(config::CMD_DISCOVER_PROFILES) => {
                        // Each config file's output is separated by NUL.
                        // Parse each independently to avoid duplicate-section TOML errors.
                        for chunk in stdout.split(|&b| b == 0) {
                            if chunk.is_empty() { continue; }
                            let content = String::from_utf8_lossy(chunk);
                            let (by_agent, details_by_agent) = config::parse_profiles_from_toml(&content);
                            self.config.merge_profiles(&by_agent, &details_by_agent);
                        }
                        true
                    }
                    Some(config::CMD_LOAD_AGENT_DEFAULTS) => {
                        let agent_types = config::parse_agent_defaults(&stdout);
                        if !agent_types.is_empty() {
                            self.config.agent_types = agent_types;
                        }
                        self.agent_types_loaded = true;
                        // Flush any buffered restore that was waiting for agent types.
                        if let Some(saved_agents) = self.pending_restore.take() {
                            self.restore_agents(saved_agents);
                        }
                        true
                    }
                    Some(sandbox_backend::CMD_DETECT_BACKEND) => {
                        if exit_code == Some(0) {
                            let detected = DetectedBackends::from_stdout(&stdout);
                            self.detected_backends = Some(detected);
                        }
                        true
                    }
                    Some(config::CMD_PATH_COMPLETE) => {
                        if let Some(ref mut wizard) = self.wizard {
                            // Discard stale results if the input changed since the request.
                            let expected = context.get("prefix").map(|s| s.as_str());
                            if expected.is_some() && expected != Some(&wizard.project_dir) {
                                return true; // stale — ignore
                            }

                            let output = String::from_utf8_lossy(&stdout);
                            let mut matches: Vec<String> = output
                                .lines()
                                .filter(|l| !l.is_empty())
                                .map(|l| config::collapse_tilde(l))
                                .collect();
                            matches.sort();

                            if matches.len() == 1 {
                                // Single match: auto-fill directly.
                                wizard.project_dir = matches.remove(0);
                                wizard.clear_completions();
                            } else if matches.len() > 1 {
                                // Fill common prefix and show candidates.
                                let prefix = config::common_prefix(&matches);
                                if prefix.len() > wizard.project_dir.len() {
                                    wizard.project_dir = prefix;
                                }
                                wizard.completions = matches;
                                wizard.completion_index = None;
                            }
                            // If no matches, leave state unchanged.
                        }
                        true
                    }
                    _ => false,
                }
            }
            _ => false,
        }
    }

    fn render(&mut self, rows: usize, cols: usize) {
        // If help overlay is active, render it and return
        if self.show_help {
            dashboard::render_help_overlay(rows, cols);
            return;
        }

        // If wizard is active, render the wizard overlay instead of the dashboard
        if let Some(ref wizard) = self.wizard {
            dashboard::render_wizard(wizard, rows, cols, &self.config.agent_types);
            return;
        }

        let config_warning = self.config_error.as_deref();
        let effective_status = self.status_message.as_deref().or(config_warning);

        let detail_id = if self.show_detail {
            self.agents.get(self.selected_index).map(|a| a.id.as_str())
        } else {
            None
        };

        dashboard::render_dashboard(
            &self.agents,
            self.selected_index,
            self.focused_agent.as_deref(),
            detail_id,
            rows,
            cols,
            effective_status,
            self.name_prompt.as_ref(),
            &self.config.agent_types,
        );
    }

    fn pipe(&mut self, pipe_message: PipeMessage) -> bool {
        // Close the CLI pipe so `zellij pipe` command can return
        unblock_cli_pipe_input(&pipe_message.name);
        cli_pipe_output(&pipe_message.name, "");

        match pipe_message.name.as_str() {
            PIPE_CLAUDE_STATUS | PIPE_LINCE_STATUS => {
                if let Some(payload) = pipe_message.payload {
                    self.handle_status_message(&payload);
                    return true;
                }
                false
            }
            PIPE_VOXCODE_TEXT => {
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
    /// Sort agents by project_dir, then by name within each group.
    /// Preserves the selected agent across the sort.
    fn sort_agents_by_dir(&mut self) {
        let selected_id = self.agents.get(self.selected_index).map(|a| a.id.clone());

        self.agents.sort_by(|a, b| {
            a.project_dir.cmp(&b.project_dir).then(a.name.cmp(&b.name))
        });

        if let Some(id) = selected_id {
            if let Some(pos) = self.agents.iter().position(|a| a.id == id) {
                self.selected_index = pos;
            }
        }
    }

    fn handle_key(&mut self, key: KeyWithModifier) -> bool {
        // If wizard is active, route all keys there
        if self.wizard.is_some() {
            return self.handle_wizard_key(key);
        }

        // If name prompt is active, route keys there (LINCE-55)
        if self.name_prompt.is_some() {
            return self.handle_name_prompt_key(key);
        }

        let bare = &key.bare_key;
        let no_mods = key.key_modifiers.is_empty();

        if !no_mods {
            return false;
        }

        match bare {
            BareKey::Char('n') => {
                let base = agent::agent_type_base_name(DEFAULT_AGENT_TYPE);
                let default_name = format!("{}-{}", base, self.next_agent_id + 1);
                self.name_prompt = Some(NamePromptState {
                    input: String::new(),
                    default_name,
                    label: "Name",
                });
                true
            }
            BareKey::Char('r') => {
                if let Some(agent) = self.agents.get(self.selected_index) {
                    self.rename_target = Some(agent.id.clone());
                    self.name_prompt = Some(NamePromptState {
                        input: String::new(),
                        default_name: agent.name.clone(),
                        label: "Rename",
                    });
                }
                true
            }
            BareKey::Char('N') => {
                let default_dir = self.config.default_project_dir.clone()
                    .unwrap_or_default();
                // Build sorted list of available agent types from config
                let mut agent_type_list: Vec<(String, String)> = self.config.agent_types.iter()
                    .map(|(k, v)| (k.clone(), v.display_name.clone()))
                    .collect();
                agent_type_list.sort_by(|a, b| a.0.cmp(&b.0));
                let default_at_index = agent_type_list.iter()
                    .position(|(k, _)| k == DEFAULT_AGENT_TYPE)
                    .unwrap_or(0);
                // Resolve profiles for the default agent type
                let default_at_key = agent_type_list.get(default_at_index)
                    .map(|(k, _)| k.as_str())
                    .unwrap_or(DEFAULT_AGENT_TYPE);
                let available_profiles = self.config.profiles_for_agent_type(default_at_key);
                let default_profile_index = self.config.default_profile.as_ref()
                    .and_then(|dp| available_profiles.iter().position(|p| p == dp))
                    .unwrap_or(0);
                // Skip agent type step if only one type available
                let first_step = if agent_type_list.len() <= 1 {
                    WizardStep::Name
                } else {
                    WizardStep::AgentType
                };
                let base = agent::agent_type_base_name(default_at_key);
                let default_name = format!("{}-{}", base, self.next_agent_id + 1);
                self.wizard = Some(WizardState {
                    step: first_step,
                    available_agent_types: agent_type_list,
                    agent_type_index: default_at_index,
                    name: String::new(),
                    default_name,
                    available_profiles,
                    profile_index: default_profile_index,
                    project_dir: default_dir,
                    completions: Vec::new(),
                    completion_index: None,
                });
                true
            }
            BareKey::Char('x') => {
                if let Some(agent) = self.agents.get(self.selected_index) {
                    let name = agent.name.clone();
                    agent::stop_agent(agent);
                    self.agents.remove(self.selected_index);
                    if self.selected_index > 0 && self.selected_index >= self.agents.len() {
                        self.selected_index = self.agents.len().saturating_sub(1);
                    }
                    self.sort_agents_by_dir();
                    self.status_message = Some(format!("Killed {}", name));
                }
                true
            }
            BareKey::Char('j') | BareKey::Down => {
                self.selected_index = wrap_next(self.selected_index, self.agents.len());
                true
            }
            BareKey::Char('k') | BareKey::Up => {
                self.selected_index = wrap_prev(self.selected_index, self.agents.len());
                true
            }
            BareKey::Char('f') | BareKey::Enter => {
                self.focus_selected();
                true
            }
            BareKey::Char('h') | BareKey::Esc => {
                // Layered dismissal: help > unfocus (detail is toggled only by 'i')
                if self.show_help {
                    self.show_help = false;
                } else {
                    self.unfocus_current();
                }
                self.status_message = None;
                true
            }
            BareKey::Char(']') => {
                self.unfocus_current();
                if let Some(new_idx) = pane_manager::focus_next(
                    &self.agents, self.selected_index, &self.config.focus_mode,
                    &self.config.agent_layout,
                ) {
                    self.selected_index = new_idx;
                    self.focused_agent = Some(self.agents[new_idx].id.clone());
                }
                true
            }
            BareKey::Char('[') => {
                self.unfocus_current();
                if let Some(new_idx) = pane_manager::focus_prev(
                    &self.agents, self.selected_index, &self.config.focus_mode,
                    &self.config.agent_layout,
                ) {
                    self.selected_index = new_idx;
                    self.focused_agent = Some(self.agents[new_idx].id.clone());
                }
                true
            }
            BareKey::Char('i') => {
                // Toggle auto-detail panel (show/hide for selected agent)
                self.show_detail = !self.show_detail;
                true
            }
            BareKey::Char('?') => {
                self.show_help = !self.show_help;
                true
            }
            BareKey::Char('Q') => {
                self.save_and_quit();
                true
            }
            // Number keys 1-9: quick select + focus agent
            BareKey::Char(c @ '1'..='9') => {
                let idx = (*c as u8 - b'1') as usize;
                if idx < self.agents.len() {
                    self.selected_index = idx;
                    self.focus_selected();
                    true
                } else {
                    false
                }
            }
            _ => false,
        }
    }

    /// Handle keyboard input while the inline name prompt is active.
    fn handle_name_prompt_key(&mut self, key: KeyWithModifier) -> bool {
        let bare = key.bare_key;
        let no_mods = key.key_modifiers.is_empty();

        if !no_mods {
            return false;
        }

        let prompt = match self.name_prompt.as_mut() {
            Some(p) => p,
            None => return false,
        };

        match bare {
            BareKey::Esc => {
                self.name_prompt = None;
                self.rename_target = None;
                return true;
            }
            BareKey::Enter => {
                let name = if prompt.input.is_empty() {
                    prompt.default_name.clone()
                } else {
                    prompt.input.clone()
                };
                self.name_prompt = None;

                if let Some(agent_id) = self.rename_target.take() {
                    // Rename mode: update agent name + Zellij pane title.
                    if let Some(agent) = self.agents.iter_mut().find(|a| a.id == agent_id) {
                        agent.name = name.clone();
                        if let Some(pid) = agent.pane_id {
                            let title = agent::pane_title(&name, &agent.agent_type, &self.config.agent_types);
                            rename_pane_with_id(PaneId::Terminal(pid), &title);
                        }
                        self.status_message = Some(format!("Renamed to {}", name));
                    }
                    self.sort_agents_by_dir();
                } else {
                    // New agent mode: spawn.
                    match agent::spawn_agent_custom(
                        &self.config,
                        &mut self.next_agent_id,
                        &self.agents,
                        name,
                        DEFAULT_AGENT_TYPE,
                        self.config.default_profile.clone(),
                        self.config
                            .default_project_dir
                            .clone()
                            .unwrap_or_default(),
                        self.launch_dir.as_deref(),
                    ) {
                        Ok(info) => {
                            self.status_message = Some(format!("Spawned {}", info.name));
                            self.agents.push(info);
                            self.sort_agents_by_dir();
                            self.hide_all_agent_panes();
                        }
                        Err(e) => {
                            self.status_message = Some(e);
                        }
                    }
                }
                return true;
            }
            BareKey::Backspace => {
                prompt.input.pop();
            }
            BareKey::Char(c) => {
                prompt.input.push(c);
            }
            _ => {}
        }
        true
    }

    /// Handle keyboard input while the wizard overlay is active.
    fn handle_wizard_key(&mut self, key: KeyWithModifier) -> bool {
        let bare = key.bare_key;
        let no_mods = key.key_modifiers.is_empty();

        if !no_mods {
            return false;
        }

        let wizard = match self.wizard.as_mut() {
            Some(w) => w,
            None => return false,
        };

        match bare {
            BareKey::Esc => {
                // If completions are showing, dismiss them instead of closing the wizard.
                if !wizard.completions.is_empty() {
                    wizard.clear_completions();
                    return true;
                }
                self.wizard = None;
                self.status_message = Some("Wizard cancelled".to_string());
                set_timeout(3.0);
                return true;
            }
            _ => {}
        }

        match wizard.step {
            WizardStep::AgentType => match bare {
                BareKey::Enter | BareKey::Tab => {
                    // Re-resolve profiles for the newly selected agent type
                    let at_key = wizard.selected_agent_type().to_string();
                    wizard.available_profiles = self.config.profiles_for_agent_type(&at_key);
                    wizard.profile_index = 0;
                    // Update default name to reflect selected agent type
                    let base = agent::agent_type_base_name(&at_key);
                    wizard.default_name = format!("{}-{}", base, self.next_agent_id + 1);
                    wizard.step = WizardStep::Name;
                }
                BareKey::Up | BareKey::Char('k') => {
                    if wizard.agent_type_index > 0 {
                        wizard.agent_type_index -= 1;
                    } else {
                        wizard.agent_type_index = wizard.available_agent_types.len().saturating_sub(1);
                    }
                }
                BareKey::Down | BareKey::Char('j') => {
                    let len = wizard.available_agent_types.len();
                    if len > 0 {
                        wizard.agent_type_index = (wizard.agent_type_index + 1) % len;
                    }
                }
                _ => {}
            },
            WizardStep::Name => match bare {
                BareKey::Enter | BareKey::Tab => {
                    if wizard.has_profiles() {
                        wizard.step = WizardStep::Profile;
                    } else {
                        wizard.step = WizardStep::ProjectDir;
                    }
                }
                BareKey::Backspace => {
                    if wizard.name.is_empty() && wizard.has_agent_types() {
                        wizard.step = WizardStep::AgentType;
                    } else {
                        wizard.name.pop();
                    }
                }
                BareKey::Char(c) => {
                    wizard.name.push(c);
                }
                _ => {}
            },
            WizardStep::Profile => match bare {
                BareKey::Enter | BareKey::Tab => {
                    wizard.step = WizardStep::ProjectDir;
                }
                BareKey::Backspace => {
                    wizard.step = WizardStep::Name;
                }
                BareKey::Up | BareKey::Char('k') => {
                    if wizard.profile_index > 0 {
                        wizard.profile_index -= 1;
                    } else {
                        wizard.profile_index = wizard.available_profiles.len().saturating_sub(1);
                    }
                }
                BareKey::Down | BareKey::Char('j') => {
                    let len = wizard.available_profiles.len();
                    if len > 0 {
                        wizard.profile_index = (wizard.profile_index + 1) % len;
                    }
                }
                _ => {}
            },
            WizardStep::ProjectDir => match bare {
                BareKey::Enter => {
                    // If completions are showing and one is highlighted, accept it first.
                    if let Some(idx) = wizard.completion_index {
                        if let Some(selected) = wizard.completions.get(idx).cloned() {
                            wizard.project_dir = selected;
                        }
                        wizard.clear_completions();
                    } else {
                        wizard.step = WizardStep::Confirm;
                    }
                }
                BareKey::Tab => {
                    if wizard.completions.is_empty() {
                        // First Tab press: request completions from the shell.
                        config::complete_path_async(&wizard.project_dir);
                    } else {
                        // Subsequent Tab presses: cycle through suggestions.
                        let len = wizard.completions.len();
                        wizard.completion_index = Some(match wizard.completion_index {
                            Some(i) => (i + 1) % len,
                            None => 0,
                        });
                    }
                }
                BareKey::Backspace => {
                    if wizard.project_dir.is_empty() {
                        if wizard.has_profiles() {
                            wizard.step = WizardStep::Profile;
                        } else {
                            wizard.step = WizardStep::Name;
                        }
                    } else {
                        wizard.project_dir.pop();
                        wizard.clear_completions();
                    }
                }
                BareKey::Char(c) => {
                    wizard.project_dir.push(c);
                    wizard.clear_completions();
                }
                _ => {}
            },
            WizardStep::Confirm => match bare {
                BareKey::Enter => {
                    // Clone values out before dropping the borrow
                    let name = wizard.name.clone();
                    let agent_type = wizard.selected_agent_type().to_string();
                    let profile = wizard.selected_profile().map(|s| s.to_string());
                    let project_dir = wizard.project_dir.clone();
                    self.wizard = None;
                    self.spawn_wizard_agent(name, &agent_type, profile, project_dir);
                    return true;
                }
                BareKey::Backspace => {
                    wizard.step = WizardStep::ProjectDir;
                }
                _ => {}
            },
        }
        true
    }

    /// Spawn an agent using custom values from the wizard.
    fn spawn_wizard_agent(
        &mut self,
        name: String,
        agent_type: &str,
        profile: Option<String>,
        project_dir: String,
    ) {
        match agent::spawn_agent_custom(
            &self.config,
            &mut self.next_agent_id,
            &self.agents,
            name,
            agent_type,
            profile,
            project_dir,
            self.launch_dir.as_deref(),
        ) {
            Ok(info) => {
                self.status_message = Some(format!("Spawned {}", info.name));
                self.agents.push(info);
                self.sort_agents_by_dir();
                self.hide_all_agent_panes();
            }
            Err(e) => {
                self.status_message = Some(e);
            }
        }
    }

    /// Focus the currently selected agent's pane.
    fn focus_selected(&mut self) {
        if let Some(agent) = self.agents.get(self.selected_index) {
            if pane_manager::focus_agent(
                agent, &self.agents, &self.config.focus_mode, &self.config.agent_layout,
            ) {
                self.focused_agent = Some(agent.id.clone());
                self.status_message = Some(format!("Focused {}", agent.name));
            }
        }
    }

    /// Hide all agent floating panes (used after spawn to prevent unwanted pane visibility).
    /// No-op in tiled mode — tiled panes should remain visible.
    fn hide_all_agent_panes(&mut self) {
        pane_manager::hide_agent_panes(&self.agents, None, &self.config.agent_layout);
        if !self.config.agent_layout.is_tiled() {
            self.focused_agent = None;
        }
    }

    /// Unfocus the currently focused agent (hide its pane).
    fn unfocus_current(&mut self) {
        if let Some(focused_id) = self.focused_agent.take() {
            if let Some(agent) = self.agents.iter().find(|a| a.id == focused_id) {
                pane_manager::unfocus_agent(agent, &self.config.focus_mode, &self.config.agent_layout);
            }
        }
    }

    /// Reload config from disk, applying all fields except sandbox_command (LINCE-51).
    fn reload_config(&mut self, path: &str) {
        let (new_cfg, err) = DashboardConfig::load(path);
        if let Some(e) = err {
            self.config_error = Some(format!("Config reload error: {}", e));
            self.status_message = Some("Config reload failed".to_string());
            return;
        }
        // Preserve fields that are not hot-reloadable or are populated at runtime.
        let sandbox_command = std::mem::take(&mut self.config.sandbox_command);
        let profiles_by_agent = std::mem::take(&mut self.config.profiles_by_agent);
        let profile_details_by_agent = std::mem::take(&mut self.config.profile_details_by_agent);
        let agent_types = std::mem::take(&mut self.config.agent_types);
        self.config = new_cfg;
        self.config.sandbox_command = sandbox_command;
        // Merge back auto-discovered profiles (they aren't in the config file).
        self.config.merge_profiles(&profiles_by_agent, &profile_details_by_agent);
        // Preserve async-loaded agent types across hot-reload.
        if self.config.agent_types.is_empty() {
            self.config.agent_types = agent_types;
        }
        self.config_error = None;
        self.status_message = Some("Config reloaded".to_string());
    }

    /// Handle a "claude-status" pipe message (LINCE-42, LINCE-48, LINCE-53).
    fn handle_status_message(&mut self, payload: &str) {
        let msg: StatusMessage = match serde_json::from_str(payload) {
            Ok(m) => m,
            Err(_) => return, // silently ignore malformed messages
        };

        let agent = match self.agents.iter_mut().find(|a| a.id == msg.agent_id) {
            Some(a) => a,
            None => return, // unknown agent, ignore
        };

        // Some agents (e.g. Codex) launch into an interactive prompt, so the
        // generic wrapper's initial "start" event can arrive before pane
        // reconciliation. Suppress only that premature start. Once the pane has
        // been matched and moved to INPUT, allow a later wrapper start to
        // transition the agent into Running.
        if msg.event == "start"
            && self.config.agent_types.get(&agent.agent_type)
                .map_or(false, |c| c.ignore_wrapper_start)
            && matches!(agent.status, AgentStatus::Starting)
        {
            return;
        }

        // LINCE-53: handle subagent start/stop events
        match msg.event.as_str() {
            "subagent_start" => {
                agent.running_subagents = agent.running_subagents.saturating_add(1);
                return;
            }
            "subagent_stop" => {
                agent.running_subagents = agent.running_subagents.saturating_sub(1);
                return;
            }
            _ => {}
        }

        let new_status = msg.to_agent_status(self.config.event_map_for(&agent.agent_type));
        agent.status = new_status;

        // LINCE-48: update detailed fields
        if let Some(tool) = msg.tool_name {
            agent.current_tool = Some(tool);
        }
        if let Some(t) = msg.tokens_in {
            agent.tokens_in = t;
        }
        if let Some(t) = msg.tokens_out {
            agent.tokens_out = t;
        }
        if let Some(e) = msg.error {
            agent.last_error = Some(e);
        }
        if let Some(m) = msg.model {
            agent.model = Some(m);
        }
        agent.apply_status_side_effects();
    }

    /// Handle a "voxcode-text" pipe message — relay text to active agent (LINCE-43).
    fn handle_voxcode_text(&mut self, text: &str) {
        // Find the target agent index: focused > selected > none
        let target_idx = if let Some(ref focused_id) = self.focused_agent {
            self.agents.iter().position(|a| &a.id == focused_id)
        } else if self.selected_index < self.agents.len() {
            Some(self.selected_index)
        } else {
            None
        };

        let Some(idx) = target_idx else {
            self.status_message = Some("No agent to receive text".to_string());
            set_timeout(3.0);
            return;
        };

        let Some(pid) = self.agents[idx].pane_id else {
            self.status_message = Some("Agent has no pane".to_string());
            set_timeout(3.0);
            return;
        };

        write_chars_to_pane_id(text, PaneId::Terminal(pid));

        // Show the agent pane after delivering text
        if pane_manager::focus_agent(
            &self.agents[idx], &self.agents,
            &self.config.focus_mode, &self.config.agent_layout,
        ) {
            self.focused_agent = Some(self.agents[idx].id.clone());
            self.selected_index = idx;
        }
    }

    /// Poll status files for all agents (file-based fallback, LINCE-42).
    /// Returns true if any agent state changed.
    fn poll_status_files(&mut self) -> bool {
        let mut changed = false;
        let status_dir = &self.config.status_file_dir;
        for agent in self.agents.iter_mut() {
            // Check both file naming conventions:
            // Claude hook writes "claude-{id}.state", wrapper writes "{id}.state"
            let path_claude = format!("{}/claude-{}.state", status_dir, agent.id);
            let path_wrapper = format!("{}/{}.state", status_dir, agent.id);
            let content_opt = std::fs::read_to_string(&path_claude)
                .or_else(|_| std::fs::read_to_string(&path_wrapper))
                .ok();
            if let Some(content) = content_opt {
                let event = content.trim().to_string();
                if !event.is_empty() {
                    // Skip if the event hasn't changed since last poll
                    if agent.last_polled_event.as_ref() == Some(&event) {
                        continue;
                    }
                    agent.last_polled_event = Some(event.clone());
                    let msg = StatusMessage {
                        agent_id: agent.id.clone(),
                        event,
                        timestamp: None,
                        tool_name: None,
                        tokens_in: None,
                        tokens_out: None,
                        error: None,
                        subagent_type: None,
                        model: None,
                    };
                    let new_status = msg.to_agent_status(self.config.event_map_for(&agent.agent_type));
                    if agent.status != new_status {
                        agent.status = new_status;
                        changed = true;
                    }
                    agent.apply_status_side_effects();
                }
            }
        }
        changed
    }

    /// Save current agent state and quit Zellij.
    /// The actual quit happens in the RunCommandResult handler after
    /// the save command completes successfully.
    fn save_and_quit(&mut self) {
        let dir = match self.launch_dir.as_deref() {
            Some(d) => d,
            None => {
                self.status_message = Some("CWD not detected yet, try again".to_string());
                set_timeout(3.0);
                return;
            }
        };

        let saved: Vec<SavedAgentInfo> = self.agents.iter()
            .filter(|a| a.status != AgentStatus::Stopped)
            .map(SavedAgentInfo::from)
            .collect();

        match state_file::save_state_async(dir, saved, self.next_agent_id) {
            Ok(()) => {
                self.status_message = Some("Saving state...".to_string());
            }
            Err(e) => {
                self.status_message = Some(format!("Save failed: {}", e));
                set_timeout(5.0);
            }
        }
    }

    /// Re-spawn agents from saved state.
    fn restore_agents(&mut self, saved_agents: Vec<SavedAgentInfo>) {
        let mut spawned = 0u32;
        for saved in saved_agents {
            match agent::spawn_agent_custom(
                &self.config,
                &mut self.next_agent_id,
                &self.agents,
                saved.name,
                &saved.agent_type,
                saved.profile,
                saved.project_dir,
                self.launch_dir.as_deref(),
            ) {
                Ok(mut info) => {
                    info.group = saved.group;
                    info.tokens_in = saved.tokens_in;
                    info.tokens_out = saved.tokens_out;
                    self.agents.push(info);
                    spawned += 1;
                }
                Err(e) => {
                    self.status_message = Some(format!("Restore error: {}", e));
                    break;
                }
            }
        }
        if spawned > 0 {
            self.sort_agents_by_dir();
            self.hide_all_agent_panes();
            // Auto-focus the first restored agent
            self.selected_index = 0;
            self.focus_selected();
            self.status_message = Some(format!("Restored {} agents", spawned));
            set_timeout(3.0);
        }
    }
}
