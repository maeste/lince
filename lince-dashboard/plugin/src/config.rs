use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::sandbox_backend::{BackendConfig, SandboxBackend};

/// Default agent type key used when no explicit type is specified.
pub const DEFAULT_AGENT_TYPE: &str = "claude";

/// Default sandbox command / pane title pattern fallback.
pub const DEFAULT_SANDBOX_COMMAND: &str = "agent-sandbox";

/// Configuration for a single agent type (e.g. "claude", "codex", "gemini").
///
/// Agent types are defined in `agents-defaults.toml` and can be overridden
/// by `[agents.<name>]` sections in the user's `config.toml`.
/// String keys only — no enum, fully data-driven.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentTypeConfig {
    /// Command template. Supports `{agent_id}`, `{project_dir}`, `{profile}` placeholders.
    pub command: Vec<String>,
    /// Pattern to match pane titles for reconciliation (e.g. "agent-sandbox").
    pub pane_title_pattern: String,
    /// Pipe name for receiving status messages (e.g. "claude-status").
    pub status_pipe_name: String,
    /// Full display name for the UI (e.g. "Claude Code").
    pub display_name: String,
    /// 3-char label for the table column header (e.g. "CLA").
    pub short_label: String,
    /// ANSI color name (e.g. "blue", "red", "cyan").
    pub color: String,
    /// Whether the agent runs inside the bwrap sandbox.
    pub sandboxed: bool,
    /// Environment variables to pass through to the agent process.
    #[serde(default)]
    pub env_vars: HashMap<String, String>,
    /// If true, agent has its own status hooks; if false, needs a wrapper.
    #[serde(default)]
    pub has_native_hooks: bool,
    /// Read-only bind mounts from $HOME (e.g. ["~/.claude/"]).
    #[serde(default)]
    pub home_ro_dirs: Vec<String>,
    /// Read-write bind mounts from $HOME (e.g. ["~/.local/share/codex/"]).
    #[serde(default)]
    pub home_rw_dirs: Vec<String>,
    /// Agent uses bwrap internally, conflicts with outer sandbox bwrap.
    #[serde(default)]
    pub bwrap_conflict: bool,
    /// Arguments to disable agent's own sandbox (e.g. ["--sandbox", "none"]).
    #[serde(default)]
    pub disable_inner_sandbox_args: Vec<String>,
    /// If true, ignore the generic wrapper's initial "start" event when the
    /// agent is still in Starting/WaitingForInput state. Useful for agents
    /// that launch into an interactive prompt (e.g. Codex).
    #[serde(default)]
    pub ignore_wrapper_start: bool,
    /// Custom mapping from agent event names to lince status strings.
    #[serde(default)]
    pub event_map: HashMap<String, String>,
    /// Sandbox profiles applicable to this agent type.
    /// - `["__discover__"]` means use all auto-discovered profiles (default for sandboxed agents via agent-sandbox).
    /// - Empty or omitted means no profiles (skip profile wizard step).
    /// - Explicit list restricts the wizard to those profile names.
    #[serde(default)]
    pub profiles: Vec<String>,
    /// Sandbox backend used by this agent type.
    /// Overrides the global `[dashboard].sandbox_backend` setting.
    /// Defaults to `AgentSandbox` for backward compatibility.
    #[serde(default)]
    pub sandbox_backend: SandboxBackend,
}

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
    DEFAULT_SANDBOX_COMMAND.to_string()
}

fn default_status_file_dir() -> String {
    "/tmp/lince-dashboard".to_string()
}

fn default_max_agents() -> usize {
    8
}

/// Parsed profile details from sandbox config (env vars to set/unset).
#[derive(Debug, Clone, Default)]
pub struct ProfileDetails {
    /// Environment variables to set (from `[profiles.<name>.env]`).
    pub env: HashMap<String, String>,
    /// Environment variables to unset (from `[profiles.<name>.env_unset]`).
    pub env_unset: Vec<String>,
}

/// Main dashboard configuration, deserialized from the `[dashboard]` TOML table.
#[derive(Debug, Clone, Deserialize)]
pub struct DashboardConfig {
    #[serde(default)]
    pub default_profile: Option<String>,
    /// Per-agent-type profile names, keyed by agent base name (e.g. "claude", "codex").
    /// Populated from `[profiles.*]` (legacy → "claude") and `[<agent>.profiles.*]`
    /// sections in the sandbox config.
    #[serde(skip)]
    pub profiles_by_agent: HashMap<String, Vec<String>>,
    /// Per-agent-type profile details (env vars), keyed by agent base name then profile name.
    #[serde(skip)]
    pub profile_details_by_agent: HashMap<String, HashMap<String, ProfileDetails>>,
    /// Path to sandbox config for profile auto-discovery.
    /// Defaults to `~/.agent-sandbox/config.toml`.
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
    /// Agent type configurations keyed by type name (e.g. "claude", "codex").
    /// Loaded asynchronously from `agents-defaults.toml`, then merged with
    /// any `[agents.<name>]` sections from the user's `config.toml`.
    #[serde(default)]
    pub agent_types: HashMap<String, AgentTypeConfig>,
    /// Global sandbox backend preference (parsed from config, not yet wired to resolution).
    #[allow(dead_code)]
    #[serde(default)]
    pub sandbox_backend: BackendConfig,
}

impl Default for DashboardConfig {
    fn default() -> Self {
        DashboardConfig {
            default_profile: None,
            profiles_by_agent: HashMap::new(),
            profile_details_by_agent: HashMap::new(),
            sandbox_config_path: None,
            default_project_dir: None,
            sandbox_command: default_sandbox_command(),
            agent_layout: AgentLayout::default(),
            focus_mode: FocusMode::default(),
            status_method: StatusMethod::default(),
            status_file_dir: default_status_file_dir(),
            max_agents: default_max_agents(),
            agent_types: HashMap::new(),
            sandbox_backend: BackendConfig::default(),
        }
    }
}

/// Wrapper matching the TOML file structure with a `[dashboard]` section.
#[derive(Deserialize)]
struct DashboardConfigFile {
    #[serde(default)]
    dashboard: DashboardConfig,
}

/// Current Unix timestamp in seconds, or 0 if unavailable (e.g. WASM).
pub fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
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

/// Convert a path that may start with `~` into a shell expression using `$HOME`.
/// Used for `run_command` scripts since the WASI sandbox lacks `$HOME` in its env.
pub fn shell_path_expr(path: &str) -> String {
    if let Some(rest) = path.strip_prefix('~') {
        format!("\"$HOME{}\"", shell_escape(rest))
    } else {
        format!("'{}'", shell_escape(path))
    }
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
/// Command type for async loading of agent type defaults via `run_command`.
pub const CMD_LOAD_AGENT_DEFAULTS: &str = "load_agent_defaults";

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

/// Extract profile details from a TOML table (the value side of a `[*.profiles.<name>]` entry).
fn parse_profile_details(profile_table: &toml::Table) -> ProfileDetails {
    let mut pd = ProfileDetails::default();
    // Parse env vars to set
    if let Some(env_table) = profile_table.get("env").and_then(|v| v.as_table()) {
        for (k, v) in env_table {
            if let Some(s) = v.as_str() {
                pd.env.insert(k.clone(), s.to_string());
            }
        }
    }
    // Parse env vars to unset
    if let Some(unset_arr) = profile_table.get("env_unset").and_then(|v| v.as_array()) {
        for v in unset_arr {
            if let Some(s) = v.as_str() {
                pd.env_unset.push(s.to_string());
            }
        }
    }
    pd
}

/// Parse sandbox profiles from TOML content, returning per-agent-type maps.
///
/// Recognises two formats:
///   - Legacy `[profiles.<name>]`          → attributed to agent base "claude"
///   - Namespaced `[<agent>.profiles.<name>]` → attributed to `<agent>`
///
/// Returns `(profiles_by_agent, details_by_agent)`.
pub fn parse_profiles_from_toml(
    content: &str,
) -> (HashMap<String, Vec<String>>, HashMap<String, HashMap<String, ProfileDetails>>) {
    let table: toml::Table = match toml::from_str(content) {
        Ok(t) => t,
        Err(_) => return (HashMap::new(), HashMap::new()),
    };

    let mut by_agent: HashMap<String, Vec<String>> = HashMap::new();
    let mut details_by_agent: HashMap<String, HashMap<String, ProfileDetails>> = HashMap::new();

    // 1) Legacy `[profiles.*]` → attributed to "claude"
    if let Some(profiles) = table.get("profiles").and_then(|v| v.as_table()) {
        let agent = "claude".to_string();
        let names = by_agent.entry(agent.clone()).or_default();
        let details = details_by_agent.entry(agent).or_default();
        for (name, value) in profiles {
            if !names.contains(name) {
                names.push(name.clone());
            }
            if let Some(profile_table) = value.as_table() {
                details.entry(name.clone()).or_insert_with(|| parse_profile_details(profile_table));
            }
        }
    }

    // 2) Namespaced `[<agent>.profiles.*]`
    // Scan all top-level keys: any that contain a `profiles` subtable are treated
    // as agent-type profile namespaces. This supports custom agent types too.
    for (key, value) in &table {
        if key == "profiles" {
            continue; // Already handled above as legacy
        }
        if let Some(agent_section) = value.as_table() {
            if let Some(profiles) = agent_section.get("profiles").and_then(|v| v.as_table()) {
                let agent = key.clone();
                let names = by_agent.entry(agent.clone()).or_default();
                let details = details_by_agent.entry(agent).or_default();
                for (name, val) in profiles {
                    if !names.contains(name) {
                        names.push(name.clone());
                    }
                    if let Some(profile_table) = val.as_table() {
                        details.entry(name.clone()).or_insert_with(|| parse_profile_details(profile_table));
                    }
                }
            }
        }
    }

    // Sort each agent's profile names
    for names in by_agent.values_mut() {
        names.sort();
    }

    (by_agent, details_by_agent)
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
    let raw_path = sandbox_config_path.unwrap_or("~/.agent-sandbox/config.toml");
    let global_expr = shell_path_expr(raw_path);

    // Output each file separated by NUL so the handler can split and parse independently.
    let mut script = format!("cat {} 2>/dev/null", global_expr);

    if let Some(dir) = launch_dir {
        let local_path = format!(
            "{}/.agent-sandbox/config.toml",
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

/// Kick off async loading of agent type defaults from
/// `~/.config/lince-dashboard/agents-defaults.toml` via `run_command`.
/// Results arrive in `Event::RunCommandResult` with context
/// `type=load_agent_defaults`.
///
/// The shell reads the defaults file first, then (separated by NUL) any
/// `[agents.*]` sections from the user's dashboard config.toml so they can
/// be merged.  User entries override defaults (full replacement per key).
pub fn load_agent_defaults_async(_sandbox_config_path: Option<&str>) {
    let defaults_path = "\"$HOME/.config/lince-dashboard/agents-defaults.toml\"";
    let user_cfg_path = "\"$HOME/.config/lince-dashboard/config.toml\"";

    // Output defaults first, then NUL, then user dashboard config (which may
    // contain [agents.*]).
    let script = format!(
        "cat {} 2>/dev/null ; printf '\\0' ; cat {} 2>/dev/null",
        defaults_path, user_cfg_path
    );

    run_typed_command(&["sh", "-c", &script], CMD_LOAD_AGENT_DEFAULTS);
}

/// TOML wrapper for user config.toml `[agents.<name>]` sections.
#[derive(Deserialize, Default)]
struct UserAgentsSection {
    #[serde(default)]
    agents: HashMap<String, AgentTypeConfig>,
}

/// Parse agent type defaults from the stdout of `load_agent_defaults_async`.
///
/// The output consists of two NUL-separated chunks:
///   1. Contents of `agents-defaults.toml` (`[agents.<name>]` tables)
///   2. Contents of user `config.toml` (may contain `[agents.<name>]` tables)
///
/// User entries override defaults (full replacement per agent type key).
pub fn parse_agent_defaults(stdout: &[u8]) -> HashMap<String, AgentTypeConfig> {
    let chunks: Vec<&[u8]> = stdout.split(|&b| b == 0).collect();

    // Parse defaults file (chunk 0) — uses [agents.<name>] structure.
    let mut agent_types: HashMap<String, AgentTypeConfig> = if let Some(chunk) = chunks.first() {
        let content = String::from_utf8_lossy(chunk);
        toml::from_str::<UserAgentsSection>(content.trim())
            .map(|s| s.agents)
            .unwrap_or_default()
    } else {
        HashMap::new()
    };

    // Parse user overrides from config.toml (chunk 1) — also [agents.<name>].
    if let Some(chunk) = chunks.get(1) {
        let content = String::from_utf8_lossy(chunk);
        if let Ok(user) = toml::from_str::<UserAgentsSection>(content.trim()) {
            for (key, val) in user.agents {
                agent_types.insert(key, val);
            }
        }
    }

    agent_types
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
    let prefix_expr = shell_path_expr(partial);

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
    /// Parse config from TOML string content. Used by async config loading
    /// (run_command cat) since std::fs is unavailable in WASI sandbox.
    pub fn parse_toml(content: &str) -> (Self, Option<String>) {
        match toml::from_str::<DashboardConfigFile>(content.trim()) {
            Ok(file) => (file.dashboard, None),
            Err(e) => (
                DashboardConfig::default(),
                Some(format!("Config parse error: {}", e)),
            ),
        }
    }


    /// Merge discovered per-agent-type profiles, deduplicating.
    pub fn merge_profiles(
        &mut self,
        by_agent: &HashMap<String, Vec<String>>,
        details_by_agent: &HashMap<String, HashMap<String, ProfileDetails>>,
    ) {
        for (agent, names) in by_agent {
            let existing = self.profiles_by_agent.entry(agent.clone()).or_default();
            for name in names {
                if !existing.contains(name) {
                    existing.push(name.clone());
                }
            }
            existing.sort();
        }
        for (agent, details) in details_by_agent {
            let existing = self.profile_details_by_agent.entry(agent.clone()).or_default();
            for (name, detail) in details {
                existing.entry(name.clone()).or_insert_with(|| detail.clone());
            }
        }
    }

    /// Resolve the effective profile list for a given agent type.
    ///
    /// - If the agent type has `profiles = ["__discover__"]`, returns discovered profiles
    ///   for the agent's base name (e.g. "claude", "codex").
    /// - If the agent type has an explicit list, returns the intersection with discovered.
    /// - If the agent type has no profiles (empty), returns an empty list.
    pub fn profiles_for_agent_type(&self, agent_type: &str) -> Vec<String> {
        let cfg = match self.agent_types.get(agent_type) {
            Some(c) => c,
            None => return Vec::new(),
        };
        if cfg.profiles.is_empty() {
            return Vec::new();
        }
        let base = crate::agent::agent_type_base_name(agent_type);
        let discovered = self.profiles_by_agent.get(base);
        if cfg.profiles.len() == 1 && cfg.profiles[0] == "__discover__" {
            return discovered.cloned().unwrap_or_default();
        }
        // Explicit list: intersect with discovered profiles for validation
        let disc = discovered.cloned().unwrap_or_default();
        cfg.profiles
            .iter()
            .filter(|p| disc.contains(p))
            .cloned()
            .collect()
    }

    /// Look up profile details for a given agent type and profile name.
    pub fn profile_details_for(&self, agent_type: &str, profile_name: &str) -> Option<&ProfileDetails> {
        let base = crate::agent::agent_type_base_name(agent_type);
        self.profile_details_by_agent
            .get(base)
            .and_then(|m| m.get(profile_name))
    }

    /// Return the event_map for a given agent type, or None if empty/missing.
    pub fn event_map_for(&self, agent_type: &str) -> Option<&HashMap<String, String>> {
        self.agent_types
            .get(agent_type)
            .map(|c| &c.event_map)
            .filter(|m| !m.is_empty())
    }
}
