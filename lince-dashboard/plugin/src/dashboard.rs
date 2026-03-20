use crate::types::{
    AgentInfo, AgentStatus, NamePromptState, WizardState, WizardStep,
};

const RESET: &str = "\x1b[0m";
const BOLD: &str = "\x1b[1m";
const REVERSE: &str = "\x1b[7m";
const BOLD_REVERSE: &str = "\x1b[1;7m";
const DIM: &str = "\x1b[2m";
const CYAN: &str = "\x1b[36m";
const KEY_COLOR: &str = "\x1b[1;36m"; // bold cyan for key hints
const BLUE_BOLD: &str = "\x1b[1;34m"; // blue bold for swimlane headers

/// Truncate a string to fit within `max_width`, appending "..." if truncated.
fn truncate(s: &str, max_width: usize) -> String {
    if max_width <= 3 {
        return s.chars().take(max_width).collect();
    }
    let char_count = s.chars().count();
    if char_count <= max_width {
        s.to_string()
    } else {
        let mut truncated: String = s.chars().take(max_width - 3).collect();
        truncated.push_str("...");
        truncated
    }
}

/// Pad or truncate a string to exactly `width` characters, left-aligned.
fn pad_left(s: &str, width: usize) -> String {
    let truncated = truncate(s, width);
    format!("{:<width$}", truncated, width = width)
}

/// Format a token count with k/M suffixes for compact display.
fn format_tokens(n: u64) -> String {
    if n >= 1_000_000 {
        format!("{:.1}M", n as f64 / 1_000_000.0)
    } else if n >= 1_000 {
        format!("{:.1}k", n as f64 / 1_000.0)
    } else {
        format!("{}", n)
    }
}

/// Compute the visible length of a string (ignoring ANSI escape sequences).
fn strip_ansi_len(s: &str) -> usize {
    let mut len = 0;
    let mut in_escape = false;
    for c in s.chars() {
        if in_escape {
            if c.is_ascii_alphabetic() {
                in_escape = false;
            }
        } else if c == '\x1b' {
            in_escape = true;
        } else {
            len += 1;
        }
    }
    len
}

/// Pad a string to exactly `width` visible characters (ANSI-aware, left-aligned).
fn pad_to_width(s: &str, width: usize) -> String {
    let visible_len = strip_ansi_len(s);
    if visible_len >= width {
        s.to_string()
    } else {
        format!("{}{}", s, " ".repeat(width - visible_len))
    }
}

/// Repeat a character n times.
fn repeat_char(c: char, n: usize) -> String {
    std::iter::repeat(c).take(n).collect()
}

/// Shorten a filesystem path by replacing $HOME with ~.
/// In WASI, std::env::var("HOME") may not work, so we gracefully skip shortening.
use crate::config::collapse_tilde;

// ── Shared overlay helpers ─────────────────────────────────────────

/// Push a title border line onto a lines buffer (e.g. `─── Title ───`).
fn push_title_border(lines: &mut Vec<String>, title: &str, w: usize) {
    let border_fill = w.saturating_sub(title.len() + 2);
    let left_border = border_fill / 2;
    let right_border = border_fill - left_border;
    lines.push(format!(
        "{}{}{}{}{}",
        BOLD,
        repeat_char('\u{2500}', left_border + 1),
        title,
        repeat_char('\u{2500}', right_border + 1),
        RESET,
    ));
}

/// Push a bordered content line (`│ content │`).
fn push_box_line(lines: &mut Vec<String>, content: &str, w: usize) {
    lines.push(format!(
        "\u{2502}{}\u{2502}",
        pad_to_width(&truncate(content, w.saturating_sub(4)), w.saturating_sub(2))
    ));
}

/// Push a bottom border (`────────`).
fn push_bottom_border(lines: &mut Vec<String>, w: usize) {
    lines.push(repeat_char('\u{2500}', w));
}

/// Render pre-built lines centered on screen.
fn render_centered_box(lines: &[String], rows: usize, cols: usize, box_width: usize) {
    let start_col = if cols > box_width { (cols - box_width) / 2 } else { 0 };
    let start_row = if rows > lines.len() { (rows - lines.len()) / 2 } else { 0 };

    for r in 0..rows {
        if r >= start_row && r < start_row + lines.len() {
            print!("{:>width$}{}", "", &lines[r - start_row], width = start_col);
            println!();
        } else {
            println!();
        }
    }
}

// ── Main dashboard ─────────────────────────────────────────────────

/// Render the full dashboard to stdout.
pub fn render_dashboard(
    agents: &[AgentInfo],
    selected: usize,
    focused: Option<&str>,
    detail: Option<&str>,
    rows: usize,
    cols: usize,
    status_message: Option<&str>,
    name_prompt: Option<&NamePromptState>,
) {
    if rows == 0 || cols == 0 {
        return;
    }

    render_header(agents.len(), cols);

    if rows < 5 {
        for _ in 1..rows.saturating_sub(1) {
            println!();
        }
        if rows > 1 {
            if let Some(prompt) = name_prompt {
                render_name_prompt_bar(prompt, cols);
            } else {
                render_status_bar(cols, status_message, agents, focused, detail);
            }
        }
        return;
    }

    println!(); // separator

    let detail_panel_rows = if detail.is_some() { 10 } else { 0 };
    let available = rows.saturating_sub(4); // header + 2 seps + statusbar
    let table_rows = available.saturating_sub(detail_panel_rows);

    if agents.is_empty() {
        render_empty_state(table_rows, cols);
    } else {
        render_agent_table(agents, selected, focused, table_rows, cols);
    }

    if let Some(detail_id) = detail {
        if let Some(agent) = agents.iter().find(|a| a.id == detail_id) {
            render_detail_panel(agent, cols, detail_panel_rows);
        }
    }

    println!(); // separator
    if let Some(prompt) = name_prompt {
        render_name_prompt_bar(prompt, cols);
    } else {
        render_status_bar(cols, status_message, agents, focused, detail);
    }
}

fn render_header(agent_count: usize, cols: usize) {
    let title = if agent_count > 0 {
        format!("LINCE Dashboard  ({} agents)", agent_count)
    } else {
        "LINCE Dashboard".to_string()
    };

    let padding_left = if cols > title.len() { (cols - title.len()) / 2 } else { 0 };
    let padding_right = cols.saturating_sub(padding_left + title.len());

    print!(
        "{}{:>left$}{}{:>right$}{}",
        BOLD_REVERSE, "", title, "", RESET,
        left = padding_left, right = padding_right,
    );
    println!();
}

fn render_empty_state(table_rows: usize, cols: usize) {
    let msg = "No agents running. Press [n] to create one.";
    let mid = table_rows / 2;

    for r in 0..table_rows {
        if r == mid {
            let msg_display = truncate(msg, cols);
            let pad = if cols > msg_display.len() { (cols - msg_display.len()) / 2 } else { 0 };
            print!("{:>width$}\x1b[33m{}{}", "", msg_display, RESET, width = pad);
            println!();
        } else {
            println!();
        }
    }
}

/// Render the agent table (#, Name, Status), grouped by project_dir swimlanes.
fn render_agent_table(
    agents: &[AgentInfo],
    selected: usize,
    focused: Option<&str>,
    table_rows: usize,
    cols: usize,
) {
    let col_idx: usize = 3;
    let col_name: usize = 20;
    let col_status: usize = 12;

    // Determine if we need swimlane headers (more than 1 unique project_dir)
    let mut unique_dirs: Vec<&str> = Vec::new();
    for a in agents {
        if !unique_dirs.contains(&a.project_dir.as_str()) {
            unique_dirs.push(&a.project_dir);
        }
    }
    let show_swimlanes = unique_dirs.len() >= 1;

    // Header row — simplified: #, Name, Status only
    let hdr = format!(
        " {} {} {}",
        pad_left("#", col_idx), pad_left("Name", col_name), pad_left("Status", col_status),
    );
    println!("{}{}{}", BOLD, truncate(&hdr, cols), RESET);

    let data_rows = table_rows.saturating_sub(1);

    // Build a list of "virtual rows": either swimlane headers or agent rows.
    // Each entry is (agent_index_or_none, swimlane_dir_or_none).
    // This lets us compute scroll offsets that account for header rows.
    let mut virtual_rows: Vec<Option<usize>> = Vec::new(); // Some(agent_idx) or None (header)
    let mut header_dirs: Vec<String> = Vec::new(); // parallel with virtual_rows for headers

    if show_swimlanes {
        let mut last_dir: Option<&str> = None;
        for (i, agent) in agents.iter().enumerate() {
            if last_dir != Some(&agent.project_dir) {
                virtual_rows.push(None);
                header_dirs.push(agent.project_dir.clone());
                last_dir = Some(&agent.project_dir);
            }
            virtual_rows.push(Some(i));
            header_dirs.push(String::new());
        }
    } else {
        for i in 0..agents.len() {
            virtual_rows.push(Some(i));
            header_dirs.push(String::new());
        }
    }

    // Find the virtual row index of the selected agent
    let selected_vrow = virtual_rows.iter().position(|v| *v == Some(selected)).unwrap_or(0);

    // Compute scroll offset in virtual row space
    let scroll_offset = if selected_vrow >= data_rows {
        // Try to keep the selected row visible, but also show its swimlane header if possible
        let mut offset = selected_vrow - data_rows + 1;
        // If the row just above offset is a header for the selected agent's swimlane, include it
        if offset > 0 && virtual_rows.get(offset.saturating_sub(1)) == Some(&None) {
            offset -= 1;
        }
        offset
    } else {
        0
    };

    let mut rendered_rows = 0;
    let mut vrow = scroll_offset;

    while rendered_rows < data_rows {
        if vrow >= virtual_rows.len() {
            println!();
            rendered_rows += 1;
            continue;
        }

        match virtual_rows[vrow] {
            None => {
                // Swimlane header row
                let dir = &header_dirs[vrow];
                let short = collapse_tilde(dir);
                let fill_len = cols.saturating_sub(short.len() + 5);
                println!(
                    " {}\u{250c} {} {}{}",
                    BLUE_BOLD, short, repeat_char('\u{2500}', fill_len), RESET,
                );
                rendered_rows += 1;
            }
            Some(agent_idx) => {
                let agent = &agents[agent_idx];

                let is_selected = agent_idx == selected;
                let is_focused = focused.map_or(false, |f| f == agent.id);
                let prefix = if is_focused { ">" } else { " " };
                let idx_str = format!("{}", agent_idx + 1);
                let status_label = agent.status.label();
                let status_color = agent.status.color();
                let subagent_suffix = if agent.running_subagents > 0 {
                    format!(" \x1b[36m{}⚙", agent.running_subagents)
                } else {
                    String::new()
                };
                let needs_attention = matches!(
                    agent.status,
                    AgentStatus::WaitingForInput | AgentStatus::PermissionRequired
                );

                if is_selected {
                    let main_before_status = format!(
                        "{}{} {}",
                        prefix, pad_left(&idx_str, col_idx), pad_left(&agent.name, col_name),
                    );
                    let status_str = pad_left(status_label, col_status);
                    let suffix_visible_len = strip_ansi_len(&subagent_suffix);
                    let plain_len = main_before_status.len() + 1 + status_str.len() + suffix_visible_len;
                    let fill = cols.saturating_sub(plain_len);

                    print!(
                        "{}{} {}{}{}{}{}{}",
                        REVERSE, main_before_status,
                        status_color, if needs_attention { BOLD } else { "" },
                        REVERSE, status_str, subagent_suffix, RESET,
                    );
                    if fill > 0 {
                        print!("{}{:>fill$}{}", REVERSE, "", RESET, fill = fill);
                    }
                    println!();
                } else {
                    // For non-selected rows, use display_name (with group suffix) in the name column
                    let name_field = if agent.group.is_some() {
                        let base = pad_left(&agent.name, col_name.saturating_sub(agent.group.as_ref().map_or(0, |g| g.len() + 3)));
                        if let Some(ref group) = agent.group {
                            format!("{} {}[{}]{}", base, DIM, group, RESET)
                        } else {
                            base
                        }
                    } else {
                        pad_left(&agent.name, col_name)
                    };

                    let line = format!(
                        "{}{} {} {}{}{}{}{}",
                        prefix, pad_left(&idx_str, col_idx), name_field,
                        status_color, if needs_attention { BOLD } else { "" },
                        pad_left(status_label, col_status), subagent_suffix, RESET,
                    );
                    println!("{}", truncate(&line, cols));
                }
                rendered_rows += 1;
            }
        }
        vrow += 1;
    }
}

/// Render the detail panel for a specific agent below the table.
fn render_detail_panel(agent: &AgentInfo, cols: usize, max_rows: usize) {
    if max_rows == 0 {
        return;
    }

    let sep: String = repeat_char('\u{2500}', cols);
    println!("{}{}{}", DIM, sep, RESET);

    let mut row = 1;

    if row < max_rows {
        println!(
            " {}Agent:{} {}  {}{}{}",
            CYAN, RESET, agent.name, agent.status.color(), agent.status.label(), RESET,
        );
        row += 1;
    }
    if row < max_rows {
        let profile = agent.profile.as_deref().unwrap_or("(default)");
        println!(" {}Profile:{} {}  {}Dir:{} {}", CYAN, RESET, profile, CYAN, RESET, agent.project_dir);
        row += 1;
    }
    if row < max_rows {
        println!(
            " {}Tokens:{} {} in / {} out",
            CYAN, RESET, format_tokens(agent.tokens_in), format_tokens(agent.tokens_out),
        );
        row += 1;
    }
    if row < max_rows {
        let tool = agent.current_tool.as_deref().unwrap_or("-");
        let subagent_info = if agent.running_subagents > 0 {
            format!("  {}Subagents:{} {}", CYAN, RESET, agent.running_subagents)
        } else {
            String::new()
        };
        println!(" {}Tool:{} {}{}", CYAN, RESET, tool, subagent_info);
        row += 1;
    }
    if row < max_rows {
        let started = agent.started_at.map_or("-".to_string(), |t| format!("{}", t));
        println!(" {}Started:{} {}", CYAN, RESET, started);
        row += 1;
    }
    if row < max_rows {
        if let Some(ref err) = agent.last_error {
            println!(" {}Error:{} \x1b[31m{}{}", CYAN, RESET, truncate(err, cols.saturating_sub(10)), RESET);
            row += 1;
        }
    }
    for _ in row..max_rows {
        println!();
    }
}

/// Render the inline name prompt as a status bar replacement (LINCE-55).
fn render_name_prompt_bar(prompt: &NamePromptState, cols: usize) {
    let cursor = "\u{2588}"; // solid block cursor
    let input_part = if prompt.input.is_empty() {
        format!("{}{}{}{}", DIM, prompt.default_name, RESET, cursor)
    } else {
        format!("{}{}", prompt.input, cursor)
    };

    let hint = if prompt.input.is_empty() {
        String::new()
    } else {
        format!("  {}(default: {}){}", DIM, prompt.default_name, RESET)
    };

    let text = format!(
        " {}{}:{} {}{}  {}[Enter]{} OK  {}[Esc]{} Cancel",
        CYAN, prompt.label, RESET, input_part, hint,
        KEY_COLOR, RESET, KEY_COLOR, RESET,
    );

    let visible_len = strip_ansi_len(&text);
    let padding = cols.saturating_sub(visible_len + 1);
    print!("\x1b[44m {}{:>pad$}{}", text, "", RESET, pad = padding);
    println!();
}

/// A key hint entry: (key label, description).
type KeyHint = (&'static str, &'static str);

/// Format a list of key hints with ANSI key coloring for the full status bar.
fn format_key_hints(hints: &[KeyHint]) -> String {
    hints
        .iter()
        .map(|(key, label)| format!("{}[{}]{} {}", KEY_COLOR, key, RESET, label))
        .collect::<Vec<_>>()
        .join("  ")
}

/// Format a list of key hints as compact text (no ANSI).
fn format_key_hints_short(hints: &[KeyHint]) -> String {
    hints
        .iter()
        .map(|(key, label)| format!("{}:{}", key, label))
        .collect::<Vec<_>>()
        .join(" ")
}

/// Return the context-appropriate key hints.
fn status_bar_hints(empty: bool, focused: bool, detail: bool) -> Vec<KeyHint> {
    if empty {
        vec![("n", "New-defaults"), ("N", "New-wizard"), ("Q", "Save+Quit"), ("?", "Help")]
    } else if focused {
        vec![("h/Esc", "Unfocus"), ("[]", "Cycle"), ("r", "Rename"), ("x", "Kill"), ("i", "Info"), ("n", "New"), ("Q", "Save+Quit"), ("?", "Help")]
    } else if detail {
        vec![("i", "Hide info"), ("f/Enter", "Focus"), ("j/k", "Nav"), ("r", "Rename"), ("x", "Kill"), ("n", "New"), ("Q", "Save+Quit"), ("?", "Help")]
    } else {
        vec![("n", "New-defaults"), ("N", "New-wizard"), ("f/Enter", "Focus"), ("r", "Rename"), ("x", "Kill"), ("i", "Info"), ("Q", "Save+Quit"), ("?", "Help")]
    }
}

/// Context-sensitive status bar.
fn render_status_bar(
    cols: usize,
    status_message: Option<&str>,
    agents: &[AgentInfo],
    focused: Option<&str>,
    detail: Option<&str>,
) {
    let is_empty = agents.is_empty();
    let is_focused = focused.is_some();
    let is_detail = detail.is_some();
    let hints = status_bar_hints(is_empty, is_focused, is_detail);

    let text = if let Some(msg) = status_message {
        let key_hints = format!(" {}", format_key_hints(&hints));
        let hints_visible = strip_ansi_len(&key_hints);
        let msg_max = cols.saturating_sub(hints_visible + 2);
        format!("{}{}", truncate(msg, msg_max), key_hints)
    } else {
        format_key_hints(&hints)
    };

    let visible_len = strip_ansi_len(&text);
    let display = if visible_len > cols.saturating_sub(2) {
        let short = format_key_hints_short(&hints);
        truncate(&short, cols.saturating_sub(2))
    } else {
        text
    };

    let display_visible = strip_ansi_len(&display);
    let padding = cols.saturating_sub(display_visible + 1);
    print!("{} {}{:>pad$}{}", REVERSE, display, "", RESET, pad = padding);
    println!();
}

// ── Overlay: Wizard (LINCE-47) ─────────────────────────────────────

pub fn render_wizard(wizard: &WizardState, rows: usize, cols: usize) {
    if rows == 0 || cols == 0 {
        return;
    }

    let box_width: usize = 60.min(cols.saturating_sub(4));
    let mut lines: Vec<String> = Vec::new();

    push_title_border(&mut lines, " New Agent Wizard ", box_width);
    push_box_line(&mut lines, "", box_width);

    let has_profiles = wizard.has_profiles();
    let total_steps: usize = if has_profiles { 4 } else { 3 };
    let (step_num, step_label) = match wizard.step {
        WizardStep::Name => (1, "Agent Name"),
        WizardStep::Profile => (2, "Profile"),
        WizardStep::ProjectDir => (if has_profiles { 3 } else { 2 }, "Project Directory"),
        WizardStep::Confirm => (total_steps, "Confirm"),
    };

    let header = format!("  Step {}/{}: {}", step_num, total_steps, step_label);
    push_box_line(&mut lines, &header, box_width);

    match wizard.step {
        WizardStep::Confirm => {
            let profile_display = wizard.selected_profile().unwrap_or("(none)");
            let dir_display = if wizard.project_dir.is_empty() { "(current dir)" } else { &wizard.project_dir };
            push_box_line(&mut lines, &format!("  Name:    {}", wizard.name), box_width);
            push_box_line(&mut lines, &format!("  Profile: {}", profile_display), box_width);
            push_box_line(&mut lines, &format!("  Dir:     {}", dir_display), box_width);
            push_box_line(&mut lines, "", box_width);
            push_box_line(&mut lines, "  [Enter] Create  [Bksp] Back  [Esc] Cancel", box_width);
        }
        WizardStep::Profile => {
            // Render profile list with selection marker
            for (i, name) in wizard.available_profiles.iter().enumerate() {
                let marker = if i == wizard.profile_index { ">" } else { " " };
                push_box_line(&mut lines, &format!("  {} {}", marker, name), box_width);
            }
            push_box_line(&mut lines, "", box_width);
            push_box_line(&mut lines, "  [j/k] Select  [Enter] Next  [Esc] Cancel", box_width);
        }
        WizardStep::ProjectDir => {
            // Horizontal scroll: show the tail of the input when it overflows.
            let input_prefix = "  > ";
            let input_suffix = "_";
            let max_visible = box_width.saturating_sub(4 + input_prefix.len() + input_suffix.len());
            let dir_display = if wizard.project_dir.chars().count() > max_visible && max_visible > 1 {
                let skip = wizard.project_dir.chars().count() - max_visible + 1;
                let s: String = wizard.project_dir.chars().skip(skip).collect();
                format!("\u{2026}{}", s) // …prefix
            } else {
                wizard.project_dir.clone()
            };
            push_box_line(&mut lines, &format!("{}{}{}", input_prefix, dir_display, input_suffix), box_width);

            // Show completion suggestions (max 5 visible).
            if !wizard.completions.is_empty() {
                let max_show = 5.min(wizard.completions.len());
                for (i, entry) in wizard.completions.iter().take(max_show).enumerate() {
                    let marker = if wizard.completion_index == Some(i) { ">" } else { " " };
                    // Truncate long paths to fit the box.
                    let max_len = box_width.saturating_sub(6);
                    let display: &str = if entry.len() > max_len {
                        // Truncate from the left (show the distinguishing tail).
                        // Advance past any mid-char byte to a valid UTF-8 boundary.
                        let mut start = entry.len() - max_len;
                        while !entry.is_char_boundary(start) && start < entry.len() {
                            start += 1;
                        }
                        &entry[start..]
                    } else {
                        entry
                    };
                    push_box_line(&mut lines, &format!("  {} {}", marker, display), box_width);
                }
                if wizard.completions.len() > max_show {
                    push_box_line(
                        &mut lines,
                        &format!("    (+{} more)", wizard.completions.len() - max_show),
                        box_width,
                    );
                }
            } else {
                push_box_line(&mut lines, "  (default: current directory)", box_width);
                push_box_line(&mut lines, "  [Tab] autocomplete path", box_width);
            }
            push_box_line(&mut lines, "", box_width);
            push_box_line(&mut lines, "  [Enter] Next  [Esc] Cancel", box_width);
        }
        WizardStep::Name => {
            // Horizontal scroll for name input too.
            let input_prefix = "  > ";
            let input_suffix = "_";
            let max_visible = box_width.saturating_sub(4 + input_prefix.len() + input_suffix.len());
            let name_display = if wizard.name.chars().count() > max_visible && max_visible > 1 {
                let skip = wizard.name.chars().count() - max_visible + 1;
                let s: String = wizard.name.chars().skip(skip).collect();
                format!("\u{2026}{}", s)
            } else {
                wizard.name.clone()
            };
            push_box_line(&mut lines, &format!("{}{}{}", input_prefix, name_display, input_suffix), box_width);
            push_box_line(&mut lines, "  (custom name or leave empty for default)", box_width);
            push_box_line(&mut lines, "", box_width);
            push_box_line(&mut lines, "  [Enter] Next  [Esc] Cancel", box_width);
        }
    }

    push_bottom_border(&mut lines, box_width);
    render_centered_box(&lines, rows, cols, box_width);
}

// ── Overlay: Help (keybinding reference) ────────────────────────────

pub fn render_help_overlay(rows: usize, cols: usize) {
    if rows == 0 || cols == 0 {
        return;
    }

    let box_width: usize = 48.min(cols.saturating_sub(4));
    let mut lines: Vec<String> = Vec::new();

    push_title_border(&mut lines, " Keybindings ", box_width);
    push_box_line(&mut lines, "", box_width);

    push_box_line(&mut lines, &format!("  {}Navigation{}", BOLD, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}j / Down{}   Move selection down", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}k / Up{}     Move selection up", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}1-9{}        Select & focus agent #", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}[ ]{}        Cycle focused agent", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, "", box_width);

    push_box_line(&mut lines, &format!("  {}Actions{}", BOLD, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}Enter / f{}  Focus agent pane", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}i{}          Toggle info panel", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}r{}          Rename selected agent", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}x{}          Kill agent", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}h / Esc{}    Unfocus / close / back", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, "", box_width);

    push_box_line(&mut lines, &format!("  {}Create{}", BOLD, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}n{}          New agent (name prompt)", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}N{}          New agent wizard", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, "", box_width);

    push_box_line(&mut lines, &format!("  {}Other{}", BOLD, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}Q{}          Save state & quit Zellij", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, &format!("  {}?{}          Toggle this help", KEY_COLOR, RESET), box_width);
    push_box_line(&mut lines, "", box_width);

    let help = format!("  Press {}?{} or {}Esc{} to close", KEY_COLOR, RESET, KEY_COLOR, RESET);
    lines.push(format!("\u{2502}{}\u{2502}", pad_to_width(&help, box_width.saturating_sub(2))));
    push_bottom_border(&mut lines, box_width);

    render_centered_box(&lines, rows, cols, box_width);
}

