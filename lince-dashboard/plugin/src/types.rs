#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
pub enum AgentStatus {
    Starting,
    Running,
    Idle,
    WaitingForInput,
    PermissionRequired,
    Stopped,
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
#[allow(dead_code)]
pub struct StatusMessage {
    pub agent_id: String,
    pub event: String,
    #[serde(default)]
    pub timestamp: Option<String>,
}

impl StatusMessage {
    /// Map the event string to an AgentStatus.
    pub fn to_agent_status(&self) -> AgentStatus {
        match self.event.as_str() {
            "stopped" | "Stop" => AgentStatus::Stopped,
            "running" | "PreToolUse" | "start" => AgentStatus::Running,
            "idle" | "idle_prompt" => AgentStatus::WaitingForInput,
            "permission" | "permission_prompt" => AgentStatus::PermissionRequired,
            _ => AgentStatus::Running,
        }
    }
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct AgentInfo {
    pub id: String,
    pub name: String,
    pub profile: Option<String>,
    pub project_dir: String,
    pub status: AgentStatus,
    pub pane_id: Option<u32>,
    pub pane_ids: Vec<u32>,
}
