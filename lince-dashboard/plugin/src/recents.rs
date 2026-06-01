//! Global "recent project directories" store for the wizard's Project dir
//! picker (#127).
//!
//! Unlike `.lince-dashboard` (per-launch-dir agent state), recents live in a
//! single global file so they follow the user regardless of which directory
//! the dashboard was launched from:
//!
//!   ~/.config/lince-dashboard/recents.json
//!
//! The file is a plain JSON array of absolute paths, most-recently-used first.
//! We intentionally store *order only* (no timestamps): wall-clock time is
//! unreliable in the WASI sandbox, and MRU order is all the picker needs.

use crate::config::run_typed_command;

pub const CMD_LOAD_RECENTS: &str = "load_recents";
pub const CMD_SAVE_RECENTS: &str = "save_recents";

/// Cap on how many recent dirs we keep / persist.
pub const MAX_RECENTS: usize = 20;

/// Shell expression for the recents file path. `$HOME` is expanded by the
/// host shell (the plugin process itself can't reliably resolve `~`/`$HOME`
/// under WASI).
const RECENTS_PATH_EXPR: &str = "\"$HOME/.config/lince-dashboard/recents.json\"";

/// Kick off an async load of the global recents file.
/// Missing file → empty stdout → `parse_loaded_recents` yields an empty list.
pub fn load_recents_async() {
    let script = format!("cat {} 2>/dev/null", RECENTS_PATH_EXPR);
    run_typed_command(&["sh", "-c", &script], CMD_LOAD_RECENTS);
}

/// Kick off an async save of the recents list, creating the parent dir if
/// needed. Writes the whole list (already trimmed to `MAX_RECENTS`).
pub fn save_recents_async(dirs: &[String]) {
    let json = match serde_json::to_string_pretty(dirs) {
        Ok(j) => j,
        Err(_) => return,
    };
    // Heredoc write avoids shell-escaping the JSON payload.
    let script = format!(
        "mkdir -p \"$HOME/.config/lince-dashboard\" && cat > {} <<'__LINCE_EOF__'\n{}\n__LINCE_EOF__",
        RECENTS_PATH_EXPR, json
    );
    run_typed_command(&["sh", "-c", &script], CMD_SAVE_RECENTS);
}

/// Parse the recents file contents. Tolerant of a missing/empty/garbage file:
/// any parse failure yields an empty list rather than an error (recents are a
/// convenience, never load-blocking).
pub fn parse_loaded_recents(stdout: &[u8]) -> Vec<String> {
    let content = String::from_utf8_lossy(stdout);
    let trimmed = content.trim();
    if trimmed.is_empty() {
        return Vec::new();
    }
    let mut parsed: Vec<String> = serde_json::from_str(trimmed).unwrap_or_default();
    // Defensive, order-preserving de-dup. `push_recent` already guarantees
    // uniqueness on write, but the file may be hand-edited or corrupted out of
    // band — keep the first occurrence of each path and cap the length.
    let mut seen = std::collections::HashSet::new();
    parsed.retain(|p| seen.insert(p.clone()));
    parsed.truncate(MAX_RECENTS);
    parsed
}

/// Record a use of `dir`: move it to the front (most-recent), de-duplicating
/// any earlier occurrence, and trim the list to `MAX_RECENTS`. Empty paths are
/// ignored. Returns `true` if the list changed (caller should persist).
pub fn push_recent(list: &mut Vec<String>, dir: &str) -> bool {
    let dir = dir.trim_end_matches('/');
    if dir.is_empty() {
        return false;
    }
    // Already at the front with nothing else to do → no change.
    if list.first().map(|s| s.as_str()) == Some(dir) {
        return false;
    }
    list.retain(|d| d != dir);
    list.insert(0, dir.to_string());
    list.truncate(MAX_RECENTS);
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_file_yields_empty() {
        assert!(parse_loaded_recents(b"").is_empty());
        assert!(parse_loaded_recents(b"   \n").is_empty());
    }

    #[test]
    fn garbage_yields_empty_not_error() {
        assert!(parse_loaded_recents(b"not json").is_empty());
    }

    #[test]
    fn round_trips_paths() {
        let parsed = parse_loaded_recents(br#"["/a/b", "/c/d"]"#);
        assert_eq!(parsed, vec!["/a/b".to_string(), "/c/d".to_string()]);
    }

    #[test]
    fn parse_dedupes_preserving_order() {
        // Hand-edited file with duplicates → first occurrence wins, order kept.
        let parsed = parse_loaded_recents(br#"["/a", "/b", "/a", "/c", "/b"]"#);
        assert_eq!(parsed, vec!["/a".to_string(), "/b".to_string(), "/c".to_string()]);
    }

    #[test]
    fn push_moves_to_front_and_dedupes() {
        let mut list = vec!["/a".to_string(), "/b".to_string()];
        assert!(push_recent(&mut list, "/b"));
        assert_eq!(list, vec!["/b", "/a"]);
        // Trailing slash is normalized, and a no-op (already front) returns false.
        assert!(!push_recent(&mut list, "/b/"));
    }

    #[test]
    fn push_caps_at_max() {
        let mut list: Vec<String> = (0..MAX_RECENTS).map(|i| format!("/p{}", i)).collect();
        assert!(push_recent(&mut list, "/new"));
        assert_eq!(list.len(), MAX_RECENTS);
        assert_eq!(list[0], "/new");
    }

    #[test]
    fn push_ignores_empty() {
        let mut list = vec!["/a".to_string()];
        assert!(!push_recent(&mut list, ""));
        assert!(!push_recent(&mut list, "/"));
    }
}
