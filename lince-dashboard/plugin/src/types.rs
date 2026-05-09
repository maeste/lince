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
///
/// Note: `Provider` selects an env-var bundle (Anthropic vs Vertex vs Z.ai
/// vs ...) — distinct from `SandboxLevel`, which selects the isolation
/// posture (paranoid/normal/permissive). The two axes are independent;
/// users can run e.g. `paranoid + zai`. See gh#81.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WizardStep {
    AgentType,
    SandboxBackend,
    SandboxLevel,
    Name,
    /// Pick the provider env-var bundle (was `Profile` pre-#81).
    Provider,
    ProjectDir,
    Confirm,
}

/// State for the multi-step "New Agent" wizard.
#[derive(Debug, Clone)]
pub struct WizardState {
    pub step: WizardStep,
    /// Available *base* agent names (deduplicated by `agent_type_base_name`),
    /// e.g. `[("claude", "Claude Code"), ("codex", "OpenAI Codex")]`. Sandbox
    /// variant suffixes (`-unsandboxed`, `-paranoid`, ...) are folded out — the
    /// wizard's SandboxBackend / SandboxLevel steps recover that information.
    pub available_agent_types: Vec<(String, String)>,
    /// Currently selected base agent index.
    pub agent_type_index: usize,
    /// Available sandbox backends for the selected agent type. Includes
    /// `SandboxBackend::None` when an `<base>-unsandboxed` entry exists.
    pub available_sandbox_backends: Vec<crate::sandbox_backend::SandboxBackend>,
    /// Currently selected sandbox backend index in `available_sandbox_backends`.
    pub sandbox_backend_index: usize,
    /// Available sandbox levels for the selected agent type (e.g. ["paranoid","normal","permissive"]).
    /// May include custom levels discovered from the filesystem (e.g. "strict").
    /// Empty for unsandboxed agents or legacy entries with no sandbox_level field.
    pub available_sandbox_levels: Vec<String>,
    /// Currently selected sandbox level index in `available_sandbox_levels`.
    pub sandbox_level_index: usize,
    pub name: String,
    /// Auto-generated default name shown when the user leaves name empty (e.g. "claude-3").
    pub default_name: String,
    /// Available providers (env-var bundles) discovered from sandbox config.
    /// Was `available_profiles` pre-#81.
    pub available_providers: Vec<String>,
    /// Currently selected provider index in `available_providers`.
    /// Was `profile_index` pre-#81.
    pub provider_index: usize,
    pub project_dir: String,
    /// Tab-completion suggestions for the project directory.
    pub completions: Vec<String>,
    /// Currently highlighted completion index (if any).
    pub completion_index: Option<usize>,
}

impl WizardState {
    /// Whether there are multiple base agent types to choose from.
    pub fn has_agent_types(&self) -> bool {
        self.available_agent_types.len() > 1
    }

    /// Return the selected *base* agent name (e.g. "claude"). Combine with
    /// `selected_sandbox_backend()` to derive the effective agent_type.
    pub fn selected_base_agent(&self) -> &str {
        self.available_agent_types
            .get(self.agent_type_index)
            .map(|(key, _)| key.as_str())
            .unwrap_or(crate::config::DEFAULT_AGENT_TYPE)
    }

    /// Resolve the effective `agent_type` config key for spawn:
    /// - `<base>-unsandboxed` when backend is `None`
    /// - `<base>` otherwise (canonical sandboxed entry)
    pub fn effective_agent_type(&self) -> String {
        let base = self.selected_base_agent();
        if matches!(
            self.selected_sandbox_backend(),
            Some(crate::sandbox_backend::SandboxBackend::None)
        ) {
            format!("{}-unsandboxed", base)
        } else {
            base.to_string()
        }
    }

    /// Whether there are multiple sandbox backends to choose from.
    pub fn has_sandbox_backends(&self) -> bool {
        self.available_sandbox_backends.len() > 1
    }

    /// Return the currently selected sandbox backend, or None if no backends available.
    pub fn selected_sandbox_backend(&self) -> Option<crate::sandbox_backend::SandboxBackend> {
        self.available_sandbox_backends.get(self.sandbox_backend_index).cloned()
    }

    /// Whether there are sandbox levels to choose from in the wizard.
    /// A single-option list is treated as "no choice" so the step is skipped —
    /// the lone level still applies, just without a useless one-row picker
    /// (see gh#91 shells, which pin `sandbox_levels = ["normal"]`).
    pub fn has_sandbox_levels(&self) -> bool {
        self.available_sandbox_levels.len() > 1
    }

    /// Return the currently selected sandbox level, or None if no levels available.
    pub fn selected_sandbox_level(&self) -> Option<&str> {
        self.available_sandbox_levels.get(self.sandbox_level_index).map(|s| s.as_str())
    }

    /// Build the ordered list of active wizard steps, applying skip rules.
    /// Used by the renderer for the step counter and by key handlers for
    /// computing prev/next steps without nested `if` arithmetic.
    pub fn active_steps(&self) -> Vec<WizardStep> {
        let mut steps = Vec::with_capacity(7);
        if self.has_agent_types() {
            steps.push(WizardStep::AgentType);
        }
        if self.has_sandbox_backends() {
            steps.push(WizardStep::SandboxBackend);
        }
        if self.has_sandbox_levels() && !self.is_unsandboxed_choice() {
            steps.push(WizardStep::SandboxLevel);
        }
        steps.push(WizardStep::Name);
        if self.has_providers() {
            steps.push(WizardStep::Provider);
        }
        steps.push(WizardStep::ProjectDir);
        steps.push(WizardStep::Confirm);
        steps
    }

    /// Whether the user has currently selected the "no sandbox" backend.
    pub fn is_unsandboxed_choice(&self) -> bool {
        matches!(
            self.selected_sandbox_backend(),
            Some(crate::sandbox_backend::SandboxBackend::None)
        )
    }

    /// Step that should follow the current one (or `None` if at end).
    pub fn next_step(&self) -> Option<WizardStep> {
        let steps = self.active_steps();
        let idx = steps.iter().position(|s| s == &self.step)?;
        steps.get(idx + 1).cloned()
    }

    /// Step that precedes the current one (or `None` if at start).
    pub fn prev_step(&self) -> Option<WizardStep> {
        let steps = self.active_steps();
        let idx = steps.iter().position(|s| s == &self.step)?;
        if idx == 0 {
            None
        } else {
            steps.get(idx - 1).cloned()
        }
    }

    /// Whether there are selectable providers (env-var bundles).
    pub fn has_providers(&self) -> bool {
        !self.available_providers.is_empty()
    }

    /// Clear any pending tab-completion state.
    pub fn clear_completions(&mut self) {
        self.completions.clear();
        self.completion_index = None;
    }

    /// Return the selected provider name, or None if no providers are available.
    /// Was `selected_profile()` pre-#81.
    pub fn selected_provider(&self) -> Option<&str> {
        self.available_providers.get(self.provider_index).map(|s| s.as_str())
    }
}

#[derive(Debug, Clone)]
pub struct AgentInfo {
    pub id: String,
    pub name: String,
    pub agent_type: String,
    /// Provider env-var bundle name selected at spawn time (was `profile`
    /// pre-#81). Distinct from `sandbox_level`, which is the isolation posture.
    pub provider: Option<String>,
    pub project_dir: String,
    pub status: AgentStatus,
    pub pane_id: Option<u32>,
    pub tokens_in: u64,
    pub tokens_out: u64,
    pub current_tool: Option<String>,
    pub started_at: Option<u64>,
    pub last_error: Option<String>,
    pub exit_code: Option<i32>,
    pub group: Option<String>,
    pub running_subagents: u32,
    pub model: Option<String>,
    /// Last event string read by poll_status_files(), used for change detection.
    pub last_polled_event: Option<String>,
    /// Runtime-selected sandbox isolation level (wizard choice or saved state).
    /// None for unsandboxed agents or legacy agents spawned without the wizard.
    pub sandbox_level: Option<String>,
    /// Runtime-selected sandbox backend (wizard choice or saved state).
    /// None means use the agent type's TOML-pinned `sandbox_backend`.
    pub sandbox_backend: Option<crate::sandbox_backend::SandboxBackend>,
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

    /// Status label with exit code annotation for stopped agents.
    pub fn status_display(&self) -> String {
        if self.status == AgentStatus::Stopped {
            match self.exit_code {
                Some(code) => format!("Stopped ({code})"),
                None => "Stopped".to_string(),
            }
        } else {
            self.status.label().to_string()
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
    /// Provider env-var bundle name. `serde(alias = "profile")` keeps
    /// pre-#81 `.lince-dashboard` files loadable.
    #[serde(default, alias = "profile")]
    pub provider: Option<String>,
    pub project_dir: String,
    pub group: Option<String>,
    pub tokens_in: u64,
    pub tokens_out: u64,
    /// Runtime sandbox level selected at spawn time. None for older state files (backward compat).
    #[serde(default)]
    pub sandbox_level: Option<String>,
    /// Runtime sandbox backend selected at spawn time. None for older state files (backward compat).
    #[serde(default)]
    pub sandbox_backend: Option<crate::sandbox_backend::SandboxBackend>,
}

fn default_agent_type() -> String {
    crate::config::DEFAULT_AGENT_TYPE.to_string()
}

impl From<&AgentInfo> for SavedAgentInfo {
    fn from(a: &AgentInfo) -> Self {
        Self {
            name: a.name.clone(),
            agent_type: a.agent_type.clone(),
            provider: a.provider.clone(),
            project_dir: a.project_dir.clone(),
            group: a.group.clone(),
            tokens_in: a.tokens_in,
            tokens_out: a.tokens_out,
            sandbox_level: a.sandbox_level.clone(),
            sandbox_backend: a.sandbox_backend.clone(),
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
