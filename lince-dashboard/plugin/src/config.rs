use serde::Deserialize;

/// Agent pane layout mode.
///
/// - `Floating` (default): agents open as floating overlay panes.
/// - `Tiled`: agents open as tiled panes in the Zellij layout grid.
///   Use with `layouts/dashboard-tiled.kdl` for a fixed split.
#[derive(Debug, Clone, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum AgentLayout {
    Floating,
    Tiled,
}

impl Default for AgentLayout {
    fn default() -> Self {
        AgentLayout::Floating
    }
}

impl AgentLayout {
    pub fn is_tiled(&self) -> bool {
        matches!(self, AgentLayout::Tiled)
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
pub struct DashboardConfig {
    #[serde(default)]
    pub default_profile: Option<String>,
    /// Available sandbox profiles for the wizard selector.
    /// Auto-discovered from sandbox config if empty.
    #[serde(default)]
    pub profiles: Vec<String>,
    /// Path to sandbox config for profile auto-discovery.
    /// Defaults to `~/.claude-sandbox/config.toml`.
    #[serde(default)]
    pub sandbox_config_path: Option<String>,
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
            profiles: Vec::new(),
            sandbox_config_path: None,
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

/// Return the modification time (Unix seconds) of a file, or 0 if unavailable.
pub fn get_file_mtime(path: &str) -> u64 {
    std::fs::metadata(path)
        .ok()
        .and_then(|m| m.modified().ok())
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Expand leading `~` to the value of `$HOME`.
pub fn expand_tilde(path: &str) -> String {
    if let Some(rest) = path.strip_prefix('~') {
        if let Ok(home) = std::env::var("HOME") {
            return format!("{}{}", home, rest);
        }
    }
    path.to_string()
}

/// Collapse `$HOME` prefix back to `~` (inverse of `expand_tilde`).
pub fn collapse_tilde(path: &str) -> String {
    if let Ok(home) = std::env::var("HOME") {
        if !home.is_empty() && path.starts_with(&home) {
            return format!("~{}", &path[home.len()..]);
        }
    }
    path.to_string()
}

/// Find the longest common prefix among a list of strings.
/// Returns an empty string if the list is empty.
/// Handles multi-byte UTF-8 correctly by snapping to char boundaries.
pub fn common_prefix(items: &[String]) -> String {
    if items.is_empty() {
        return String::new();
    }
    let first = items[0].as_bytes();
    let mut prefix_len = first.len();
    for item in &items[1..] {
        let bytes = item.as_bytes();
        prefix_len = prefix_len.min(bytes.len());
        for i in 0..prefix_len {
            if first[i] != bytes[i] {
                prefix_len = i;
                break;
            }
        }
    }
    // Snap back to a valid UTF-8 char boundary.
    while prefix_len > 0 && !items[0].is_char_boundary(prefix_len) {
        prefix_len -= 1;
    }
    items[0][..prefix_len].to_string()
}

/// Context key for identifying RunCommandResult callbacks (shared with state_file).
pub const CMD_TYPE_KEY: &str = "type";
/// Command type for async profile discovery via `run_command`.
pub const CMD_DISCOVER_PROFILES: &str = "discover_profiles";

/// Run a command with a typed context map. Wraps the common
/// BTreeMap + `run_command` boilerplate used across modules.
pub fn run_typed_command(args: &[&str], cmd_type: &str) {
    run_typed_command_with(args, cmd_type, &[]);
}

/// Run a command with a typed context map plus extra key-value pairs.
pub fn run_typed_command_with(args: &[&str], cmd_type: &str, extra: &[(&str, &str)]) {
    use std::collections::BTreeMap;
    use zellij_tile::prelude::run_command;

    let mut ctx = BTreeMap::new();
    ctx.insert(CMD_TYPE_KEY.to_string(), cmd_type.to_string());
    for &(k, v) in extra {
        ctx.insert(k.to_string(), v.to_string());
    }
    run_command(args, ctx);
}

/// Command type for async path tab-completion via `run_command`.
pub const CMD_PATH_COMPLETE: &str = "path_complete";

/// Parse sandbox profile names from TOML content (e.g. from `cat` output).
///
/// Looks for `[profiles.<name>]` tables and returns sorted profile names.
/// Returns an empty vec on any error (parse error, no profiles section, etc.).
pub fn parse_profiles_from_toml(content: &str) -> Vec<String> {
    let table: toml::Table = match toml::from_str(content) {
        Ok(t) => t,
        Err(_) => return Vec::new(),
    };

    let profiles = match table.get("profiles").and_then(|v| v.as_table()) {
        Some(p) => p,
        None => return Vec::new(),
    };

    let mut names: Vec<String> = profiles.keys().cloned().collect();
    names.sort();
    names
}

/// Escape a string for use inside single quotes in a shell command.
pub fn shell_escape(s: &str) -> String {
    s.replace('\'', "'\\''")
}

/// Kick off async discovery of sandbox profiles by reading config files
/// via `run_command`. Results arrive in `Event::RunCommandResult` with
/// context `type=discover_profiles`.
///
/// Reads the global config and optionally a project-local config. Each file
/// is cat'd separately and their outputs are joined by a NUL byte so the
/// handler can parse them independently (avoiding invalid TOML from
/// concatenating files with duplicate `[profiles]` headers).
pub fn discover_profiles_async(sandbox_config_path: Option<&str>, launch_dir: Option<&str>) {
    // Build the global config path for the shell script.
    // IMPORTANT: We must NOT quote paths that start with `~` because the shell
    // only performs tilde expansion on unquoted tildes.  `expand_tilde()` uses
    // `std::env::var("HOME")` which is unavailable inside the WASI sandbox, so
    // the tilde would be passed through literally.  Instead we let the shell
    // handle `~` expansion by using `$HOME` in the script.
    let raw_path = sandbox_config_path.unwrap_or("~/.claude-sandbox/config.toml");
    let global_expr = if let Some(rest) = raw_path.strip_prefix('~') {
        // Use $HOME so the *shell* resolves the home directory.
        format!("\"$HOME{}\"", shell_escape(rest))
    } else {
        format!("'{}'", shell_escape(raw_path))
    };

    // Output each file separated by NUL so the handler can split and parse independently.
    let mut script = format!("cat {} 2>/dev/null", global_expr);

    if let Some(dir) = launch_dir {
        let local_path = format!(
            "{}/.claude-sandbox/config.toml",
            dir.trim_end_matches('/')
        );
        script = format!(
            "{} ; printf '\\0' ; cat '{}' 2>/dev/null",
            script,
            shell_escape(&local_path)
        );
    }

    run_typed_command(&["sh", "-c", &script], CMD_DISCOVER_PROFILES);
}

/// Kick off async path tab-completion for the wizard project directory.
///
/// Lists directories matching `partial*` (with tilde expansion). Results
/// arrive in `Event::RunCommandResult` with context `type=path_complete`.
///
/// - If `partial` ends with `/`, lists subdirectories inside that directory.
/// - Otherwise, lists directories whose names start with `partial`.
/// Maximum number of completion results returned by the shell.
const MAX_COMPLETIONS: usize = 50;

pub fn complete_path_async(partial: &str) {
    // Build a shell expression for the prefix. Use `$HOME` instead of
    // `expand_tilde()` so the *shell* resolves `~` (the WASI sandbox
    // doesn't have $HOME in its environment).
    let prefix_expr = if let Some(rest) = partial.strip_prefix('~') {
        format!("\"$HOME{}\"", shell_escape(rest))
    } else {
        format!("'{}'", shell_escape(partial))
    };

    // Glob for directories matching the prefix. The trailing `*/` ensures
    // only directories are matched. Limit output to avoid unbounded results
    // on directories with many children (e.g. /usr/share/).
    let script = format!(
        "for d in {}*/; do [ -d \"$d\" ] && echo \"$d\"; done 2>/dev/null | head -n {}",
        prefix_expr,
        MAX_COMPLETIONS
    );

    // Store the request prefix so the handler can detect stale results.
    run_typed_command_with(
        &["sh", "-c", &script],
        CMD_PATH_COMPLETE,
        &[("prefix", partial)],
    );
}

impl DashboardConfig {
    /// Load configuration from a TOML file at `path`.
    ///
    /// Returns `(config, error)` where `error` is `Some(msg)` if reading or
    /// parsing failed (in which case `config` holds all defaults).
    ///
    /// Profile auto-discovery happens asynchronously via `discover_profiles_async()`
    /// after the plugin has permissions and knows the launch directory.
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
            Ok(file) => {
                let config = file.dashboard;
                // Profile discovery happens async — see discover_profiles_async().
                (config, None)
            }
            Err(e) => (
                DashboardConfig::default(),
                Some(format!("Failed to parse config '{}': {}", path, e)),
            ),
        }
    }

    /// Merge discovered profile names into `self.profiles`, deduplicating.
    pub fn merge_profiles(&mut self, discovered: &[String]) {
        for name in discovered {
            if !self.profiles.contains(name) {
                self.profiles.push(name.clone());
            }
        }
    }
}
