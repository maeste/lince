#[derive(Debug, Clone, PartialEq)]
pub enum AgentStatus {
    Starting,
    Running,
    #[allow(dead_code)] // mapped from hook events, not all paths trigger currently
    Idle,
    WaitingForInput,
    PermissionRequired,
    Stopped,
    #[allow(dead_code)] // reserved for error reporting from hooks
    Error(String),
}

impl AgentStatus {
    /// Returns ANSI color code for this status
    pub fn color(&self) -> &str {
        match self {
            AgentStatus::Starting => "\x1b[36m",            // cyan
            AgentStatus::Running => "\x1b[32m",             // green
            AgentStatus::Idle => "\x1b[33m",                // yellow
            AgentStatus::WaitingForInput => "\x1b[1;33m",   // bold yellow
            AgentStatus::PermissionRequired => "\x1b[1;31m", // bold red
            AgentStatus::Stopped => "\x1b[2m",              // dim
            AgentStatus::Error(_) => "\x1b[31m",            // red
        }
    }

    /// Human-readable label
    pub fn label(&self) -> &str {
        match self {
            AgentStatus::Starting => "Starting",
            AgentStatus::Running => "Running",
            AgentStatus::Idle => "Idle",
            AgentStatus::WaitingForInput => "INPUT",
            AgentStatus::PermissionRequired => "PERMISSION",
            AgentStatus::Stopped => "Stopped",
            AgentStatus::Error(_) => "Error",
        }
    }
}

/// Status message received from Claude Code hooks via zellij pipe or file.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct StatusMessage {
    pub agent_id: String,
    pub event: String,
    #[serde(default)]
    #[allow(dead_code)] // deserialized from hook JSON, reserved for elapsed time display
    pub timestamp: Option<String>,
    #[serde(default)]
    pub tool_name: Option<String>,
    #[serde(default)]
    pub tokens_in: Option<u64>,
    #[serde(default)]
    pub tokens_out: Option<u64>,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    #[allow(dead_code)] // deserialized from hook JSON, reserved for subagent type display
    pub subagent_type: Option<String>,
    #[serde(default)]
    pub model: Option<String>,
}

/// Map a canonical status string to AgentStatus.
/// Used for event_map values and as the first pass for raw event matching.
fn canonical_status(s: &str) -> Option<AgentStatus> {
    match s {
        "stopped" => Some(AgentStatus::Stopped),
        "running" | "start" => Some(AgentStatus::Running),
        "idle" | "waiting_for_input" => Some(AgentStatus::WaitingForInput),
        "permission" | "permission_required" => Some(AgentStatus::PermissionRequired),
        _ => None,
    }
}

impl StatusMessage {
    /// Map the event string to an AgentStatus.
    /// Priority: custom event_map → canonical names → Claude-specific aliases → Running.
    pub fn to_agent_status(&self, event_map: Option<&std::collections::HashMap<String, String>>) -> AgentStatus {
        // 1. Custom event_map lookup
        if let Some(map) = event_map {
            if let Some(mapped) = map.get(&self.event) {
                return canonical_status(mapped).unwrap_or(AgentStatus::Running);
            }
        }
        // 2. Canonical status names
        if let Some(status) = canonical_status(&self.event) {
            return status;
        }
        // 3. Claude Code-specific aliases
        match self.event.as_str() {
            "Stop" => AgentStatus::Stopped,
            "PreToolUse" => AgentStatus::Running,
            "idle_prompt" => AgentStatus::WaitingForInput,
            "permission_prompt" => AgentStatus::PermissionRequired,
            _ => AgentStatus::Running,
        }
    }
}

/// State for the inline name/rename prompt.
#[derive(Debug, Clone)]
pub struct NamePromptState {
    pub input: String,
    pub default_name: String,
    /// Label shown before the input (e.g. "Name" or "Rename").
    pub label: &'static str,
}

/// Which step the wizard is currently on.
#[derive(Debug, Clone)]
pub enum WizardStep {
    AgentType,
    Name,
    Profile,
    ProjectDir,
    Confirm,
}

/// State for the multi-step "New Agent" wizard.
#[derive(Debug, Clone)]
pub struct WizardState {
    pub step: WizardStep,
    /// Available agent type keys (from config.agent_types).
    pub available_agent_types: Vec<(String, String)>,  // (key, display_name)
    /// Currently selected agent type index.
    pub agent_type_index: usize,
    pub name: String,
    /// Auto-generated default name shown when the user leaves name empty (e.g. "claude-3").
    pub default_name: String,
    /// Available sandbox profiles (from config).
    pub available_profiles: Vec<String>,
    /// Currently selected profile index in `available_profiles`.
    pub profile_index: usize,
    pub project_dir: String,
    /// Tab-completion suggestions for the project directory.
    pub completions: Vec<String>,
    /// Currently highlighted completion index (if any).
    pub completion_index: Option<usize>,
}

impl WizardState {
    /// Whether there are multiple agent types to choose from.
    pub fn has_agent_types(&self) -> bool {
        self.available_agent_types.len() > 1
    }

    /// Return the selected agent type key, or the default as fallback.
    pub fn selected_agent_type(&self) -> &str {
        self.available_agent_types
            .get(self.agent_type_index)
            .map(|(key, _)| key.as_str())
            .unwrap_or(crate::config::DEFAULT_AGENT_TYPE)
    }

    /// Whether there are selectable profiles.
    pub fn has_profiles(&self) -> bool {
        !self.available_profiles.is_empty()
    }

    /// Clear any pending tab-completion state.
    pub fn clear_completions(&mut self) {
        self.completions.clear();
        self.completion_index = None;
    }

    /// Return the selected profile name, or None if no profiles are available.
    pub fn selected_profile(&self) -> Option<&str> {
        self.available_profiles.get(self.profile_index).map(|s| s.as_str())
    }
}

#[derive(Debug, Clone)]
pub struct AgentInfo {
    pub id: String,
    pub name: String,
    pub agent_type: String,
    pub profile: Option<String>,
    pub project_dir: String,
    pub status: AgentStatus,
    pub pane_id: Option<u32>,
    pub tokens_in: u64,
    pub tokens_out: u64,
    pub current_tool: Option<String>,
    pub started_at: Option<u64>,
    pub last_error: Option<String>,
    pub group: Option<String>,
    pub running_subagents: u32,
    pub model: Option<String>,
    /// Last event string read by poll_status_files(), used for change detection.
    pub last_polled_event: Option<String>,
}

impl AgentInfo {
    /// Clear transient fields based on current status.
    /// Call after any status change to keep derived state consistent.
    pub fn apply_status_side_effects(&mut self) {
        if matches!(
            self.status,
            AgentStatus::WaitingForInput | AgentStatus::Idle | AgentStatus::Stopped
        ) {
            self.current_tool = None;
        }
        if matches!(self.status, AgentStatus::Stopped) {
            self.running_subagents = 0;
        }
    }
}

// ── Save/Restore Types ───────────────────────────────────────────────

/// Persistable subset of AgentInfo for save-and-quit.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SavedAgentInfo {
    pub name: String,
    /// Agent type key referencing AgentTypeConfig in config. Defaults to DEFAULT_AGENT_TYPE for v1 compat.
    #[serde(default = "default_agent_type")]
    pub agent_type: String,
    pub profile: Option<String>,
    pub project_dir: String,
    pub group: Option<String>,
    pub tokens_in: u64,
    pub tokens_out: u64,
}

fn default_agent_type() -> String {
    crate::config::DEFAULT_AGENT_TYPE.to_string()
}

impl From<&AgentInfo> for SavedAgentInfo {
    fn from(a: &AgentInfo) -> Self {
        Self {
            name: a.name.clone(),
            agent_type: a.agent_type.clone(),
            profile: a.profile.clone(),
            project_dir: a.project_dir.clone(),
            group: a.group.clone(),
            tokens_in: a.tokens_in,
            tokens_out: a.tokens_out,
        }
    }
}

/// Top-level saved state written to `.lince-dashboard`.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SavedState {
    pub version: u32,
    pub agents: Vec<SavedAgentInfo>,
    pub next_agent_id: u32,
}
