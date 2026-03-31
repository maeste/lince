use serde::{Deserialize, Serialize};

/// Supported sandbox backend types.
///
/// Each backend provides a different isolation mechanism:
/// - `AgentSandbox` uses Bubblewrap (bwrap) on Linux
/// - `Nono` uses Landlock LSM on Linux and Seatbelt on macOS
/// - `None` means the agent runs without any sandbox
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SandboxBackend {
    /// Bubblewrap-based sandbox (Linux only). This is the original agent-sandbox.
    #[serde(alias = "agent-sandbox", alias = "bwrap")]
    AgentSandbox,
    /// Landlock/Seatbelt sandbox via nono (Linux + macOS).
    Nono,
    /// No sandbox — agent runs directly on the host.
    None,
}

impl Default for SandboxBackend {
    fn default() -> Self {
        SandboxBackend::AgentSandbox
    }
}

impl SandboxBackend {
    /// Short display name for the UI (shown next to agent type in the table).
    pub fn display_name(&self) -> &str {
        match self {
            SandboxBackend::AgentSandbox => "bwrap",
            SandboxBackend::Nono => "nono",
            SandboxBackend::None => "none",
        }
    }
}

/// Configuration for how the dashboard selects the sandbox backend.
///
/// Used at the `[dashboard]` level to set a global default. Individual
/// agent types can override this with their own `sandbox_backend` field.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum BackendConfig {
    /// Auto-detect based on OS and available tools.
    /// On macOS, prefers nono. On Linux, prefers agent-sandbox.
    Auto,
    /// Use agent-sandbox (bwrap) for all sandboxed agents.
    #[serde(alias = "agent-sandbox", alias = "bwrap")]
    AgentSandbox,
    /// Use nono for all sandboxed agents.
    Nono,
}

impl Default for BackendConfig {
    fn default() -> Self {
        BackendConfig::Auto
    }
}

/// Command type for async backend detection via `run_command`.
pub const CMD_DETECT_BACKEND: &str = "detect_backend";

/// Kick off async detection of available sandbox backends.
///
/// Checks for `agent-sandbox` and `nono` in PATH. Results arrive in
/// `Event::RunCommandResult` with context `type=detect_backend`.
pub fn detect_backend_async() {
    let script = concat!(
        "echo -n 'agent-sandbox:'; command -v agent-sandbox >/dev/null 2>&1 && echo 'yes' || echo 'no'; ",
        "echo -n 'nono:'; command -v nono >/dev/null 2>&1 && echo 'yes' || echo 'no'; ",
        "echo -n 'os:'; uname -s 2>/dev/null || echo 'unknown'"
    );
    crate::config::run_typed_command(&["sh", "-c", script], CMD_DETECT_BACKEND);
}

/// Result of async backend detection.
#[derive(Debug, Clone, Default)]
pub struct DetectedBackends {
    pub has_agent_sandbox: bool,
    pub has_nono: bool,
    pub os: String,
}

impl DetectedBackends {
    /// Parse the output of `detect_backend_async`.
    pub fn from_stdout(stdout: &[u8]) -> Self {
        let output = String::from_utf8_lossy(stdout);
        let mut result = DetectedBackends::default();
        for line in output.lines() {
            if let Some(val) = line.strip_prefix("agent-sandbox:") {
                result.has_agent_sandbox = val.trim() == "yes";
            } else if let Some(val) = line.strip_prefix("nono:") {
                result.has_nono = val.trim() == "yes";
            } else if let Some(val) = line.strip_prefix("os:") {
                result.os = val.trim().to_string();
            }
        }
        result
    }
}
