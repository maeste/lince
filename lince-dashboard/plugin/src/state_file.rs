use crate::config::{run_typed_command, shell_escape};
use crate::types::{SavedAgentInfo, SavedState};

const STATE_FILE_NAME: &str = ".lince-dashboard";
const STATE_VERSION: u32 = 2;

pub const CMD_SAVE_STATE: &str = "save_state";
pub const CMD_LOAD_STATE: &str = "load_state";
pub const CMD_DELETE_STATE: &str = "delete_state";

/// Build the state file path from the launch directory.
fn state_file_path(launch_dir: &str) -> String {
    format!("{}/{}", launch_dir.trim_end_matches('/'), STATE_FILE_NAME)
}

/// Kick off an async save of agent state via `run_command`.
/// The actual write happens on the host side via `sh -c 'printf ... > file'`.
/// The plugin receives the result in `Event::RunCommandResult` with context
/// `type=save_state`.
pub fn save_state_async(
    launch_dir: &str,
    agents: Vec<SavedAgentInfo>,
    next_agent_id: u32,
) -> Result<(), String> {
    let path = state_file_path(launch_dir);

    let state = SavedState {
        version: STATE_VERSION,
        agents,
        next_agent_id,
    };

    let json =
        serde_json::to_string_pretty(&state).map_err(|e| format!("Serialize error: {}", e))?;

    // Use sh -c with a heredoc-style write to avoid shell escaping issues.
    let script = format!(
        "cat > '{}' <<'__LINCE_EOF__'\n{}\n__LINCE_EOF__",
        shell_escape(&path),
        json
    );

    run_typed_command(&["sh", "-c", &script], CMD_SAVE_STATE);

    Ok(())
}

/// Kick off an async load of saved state via `run_command`.
/// The plugin receives stdout (file contents) in `Event::RunCommandResult`
/// with context `type=load_state`.
pub fn load_state_async(launch_dir: &str) {
    let path = state_file_path(launch_dir);
    run_typed_command(&["cat", &path], CMD_LOAD_STATE);
}

/// Delete the state file (currently unused but kept for future use).
#[allow(dead_code)]
pub fn delete_state_file_async(launch_dir: &str) {
    let path = state_file_path(launch_dir);
    run_typed_command(&["rm", "-f", &path], CMD_DELETE_STATE);
}

/// Parse loaded state from stdout bytes returned by `cat`.
/// Supports both v1 (no agent_type field) and v2 (with agent_type) formats.
/// v1 entries get `agent_type = "claude"` via serde default.
pub fn parse_loaded_state(stdout: &[u8]) -> Result<SavedState, String> {
    let content = String::from_utf8_lossy(stdout);
    let mut state: SavedState =
        serde_json::from_str(content.trim()).map_err(|e| format!("Parse error: {}", e))?;
    // Normalize version to current — v1 files are transparently upgraded
    state.version = STATE_VERSION;
    Ok(state)
}
