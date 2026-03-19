use serde::Deserialize;

/// Agent pane layout mode.
#[derive(Debug, Clone, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum AgentLayout {
    Single,
    Multi,
}

impl Default for AgentLayout {
    fn default() -> Self {
        AgentLayout::Single
    }
}

/// How to show the focused agent pane.
#[derive(Debug, Clone, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum FocusMode {
    Replace,
    Floating,
}

impl Default for FocusMode {
    fn default() -> Self {
        FocusMode::Floating
    }
}

/// How the plugin detects agent status changes.
#[derive(Debug, Clone, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum StatusMethod {
    Pipe,
    File,
}

impl Default for StatusMethod {
    fn default() -> Self {
        StatusMethod::Pipe
    }
}

fn default_sandbox_command() -> String {
    "claude-sandbox".to_string()
}

fn default_status_file_dir() -> String {
    "/tmp/lince-dashboard".to_string()
}

fn default_max_agents() -> usize {
    8
}

/// Main dashboard configuration, deserialized from the `[dashboard]` TOML table.
#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct DashboardConfig {
    #[serde(default)]
    pub default_profile: Option<String>,
    #[serde(default)]
    pub default_project_dir: Option<String>,
    #[serde(default = "default_sandbox_command")]
    pub sandbox_command: String,
    #[serde(default)]
    pub agent_layout: AgentLayout,
    #[serde(default)]
    pub focus_mode: FocusMode,
    #[serde(default)]
    pub status_method: StatusMethod,
    #[serde(default = "default_status_file_dir")]
    pub status_file_dir: String,
    #[serde(default = "default_max_agents")]
    pub max_agents: usize,
}

impl Default for DashboardConfig {
    fn default() -> Self {
        DashboardConfig {
            default_profile: None,
            default_project_dir: None,
            sandbox_command: default_sandbox_command(),
            agent_layout: AgentLayout::default(),
            focus_mode: FocusMode::default(),
            status_method: StatusMethod::default(),
            status_file_dir: default_status_file_dir(),
            max_agents: default_max_agents(),
        }
    }
}

/// Wrapper matching the TOML file structure with a `[dashboard]` section.
#[derive(Deserialize)]
struct DashboardConfigFile {
    #[serde(default)]
    dashboard: DashboardConfig,
}

impl DashboardConfig {
    /// Load configuration from a TOML file at `path`.
    ///
    /// Returns `(config, error)` where `error` is `Some(msg)` if reading or
    /// parsing failed (in which case `config` holds all defaults).
    ///
    /// # Manual testing
    ///
    /// 1. Place a valid `config.toml` next to the plugin WASM and pass
    ///    `config_path "/path/to/config.toml"` in the Zellij layout KDL.
    /// 2. Verify the plugin loads without warnings in the status bar.
    /// 3. Introduce a syntax error in the TOML and reload — a yellow
    ///    warning line should appear in the dashboard render output.
    /// 4. Remove the file entirely — plugin should start with defaults.
    pub fn load(path: &str) -> (Self, Option<String>) {
        let content = match std::fs::read_to_string(path) {
            Ok(c) => c,
            Err(e) => {
                return (
                    DashboardConfig::default(),
                    Some(format!("Failed to read config '{}': {}", path, e)),
                );
            }
        };

        match toml::from_str::<DashboardConfigFile>(&content) {
            Ok(file) => (file.dashboard, None),
            Err(e) => (
                DashboardConfig::default(),
                Some(format!("Failed to parse config '{}': {}", path, e)),
            ),
        }
    }
}
