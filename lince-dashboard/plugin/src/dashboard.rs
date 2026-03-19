use crate::types::{AgentInfo, AgentStatus};

const RESET: &str = "\x1b[0m";
const BOLD: &str = "\x1b[1m";
const REVERSE: &str = "\x1b[7m";
const BOLD_REVERSE: &str = "\x1b[1;7m";

/// Truncate a string to fit within `max_width`, appending "..." if truncated.
fn truncate(s: &str, max_width: usize) -> String {
    if max_width <= 3 {
        return s.chars().take(max_width).collect();
    }
    if s.len() <= max_width {
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

/// Render the full dashboard to stdout.
pub fn render_dashboard(
    agents: &[AgentInfo],
    selected: usize,
    focused: Option<&str>,
    rows: usize,
    cols: usize,
    input_mode: bool,
    status_message: Option<&str>,
) {
    if rows == 0 || cols == 0 {
        return;
    }

    // Row 0: Header
    render_header(agents.len(), cols);

    if rows < 5 {
        for _ in 1..rows.saturating_sub(1) {
            println!();
        }
        if rows > 1 {
            render_command_bar(cols, input_mode, status_message);
        }
        return;
    }

    // Row 1: separator
    println!();

    let table_rows = rows.saturating_sub(4); // header(1) + sep(1) + sep(1) + cmdbar(1)

    if agents.is_empty() {
        render_empty_state(table_rows, cols);
    } else {
        render_agent_table(agents, selected, focused, table_rows, cols);
    }

    // separator
    println!();

    // command bar
    render_command_bar(cols, input_mode, status_message);
}

fn render_header(agent_count: usize, cols: usize) {
    let title = if agent_count > 0 {
        format!("LINCE Dashboard  ({} agents)", agent_count)
    } else {
        "LINCE Dashboard".to_string()
    };

    let padding_left = if cols > title.len() {
        (cols - title.len()) / 2
    } else {
        0
    };
    let padding_right = cols.saturating_sub(padding_left + title.len());

    print!(
        "{}{:>left$}{}{:>right$}{}",
        BOLD_REVERSE,
        "",
        title,
        "",
        RESET,
        left = padding_left,
        right = padding_right,
    );
    println!();
}

fn render_empty_state(table_rows: usize, cols: usize) {
    let msg = "No agents running. Press [n] to create one.";
    let mid = table_rows / 2;

    for r in 0..table_rows {
        if r == mid {
            let msg_display = truncate(msg, cols);
            let pad = if cols > msg_display.len() {
                (cols - msg_display.len()) / 2
            } else {
                0
            };
            print!("{:>width$}\x1b[33m{}{}", "", msg_display, RESET, width = pad);
            println!();
        } else {
            println!();
        }
    }
}

/// Render the agent table. Status is right after name for visibility.
///
/// Layout: `>  # | Name        | Status     | Profile  | Project`
fn render_agent_table(
    agents: &[AgentInfo],
    selected: usize,
    focused: Option<&str>,
    table_rows: usize,
    cols: usize,
) {
    let narrow = cols < 50;

    // Column widths — status is now EARLY (after name) for visibility
    let col_idx: usize = 3;
    let col_name: usize = if narrow { 12 } else { 14 };
    let col_status: usize = 12;
    let col_profile: usize = if narrow { 0 } else { 10 };
    // Project gets remaining space
    let fixed = 1 + col_idx + 1 + col_name + 1 + col_status + 1 + col_profile + 1; // prefix + gaps
    let col_project: usize = cols.saturating_sub(fixed);

    // Header row
    if narrow {
        let hdr = format!(
            " {} {} {}",
            pad_left("#", col_idx),
            pad_left("Name", col_name),
            pad_left("Status", col_status),
        );
        println!("{}{}{}", BOLD, truncate(&hdr, cols), RESET);
    } else {
        let hdr = format!(
            " {} {} {} {} {}",
            pad_left("#", col_idx),
            pad_left("Name", col_name),
            pad_left("Status", col_status),
            pad_left("Profile", col_profile),
            pad_left("Project", col_project),
        );
        println!("{}{}{}", BOLD, truncate(&hdr, cols), RESET);
    }

    let data_rows = table_rows.saturating_sub(1);

    // Scroll offset
    let scroll_offset = if selected >= data_rows {
        selected - data_rows + 1
    } else {
        0
    };

    for i in 0..data_rows {
        let agent_idx = scroll_offset + i;
        if agent_idx >= agents.len() {
            println!();
            continue;
        }

        let agent = &agents[agent_idx];
        let is_selected = agent_idx == selected;
        let is_focused = focused.map_or(false, |f| f == agent.id);

        let prefix = if is_focused { ">" } else { " " };
        let idx_str = format!("{}", agent_idx + 1);
        let profile_str = agent.profile.as_deref().unwrap_or("-");
        let status_label = agent.status.label();
        let status_color = agent.status.color();
        let needs_attention = matches!(
            agent.status,
            AgentStatus::WaitingForInput | AgentStatus::PermissionRequired
        );

        // Build the line with status RIGHT AFTER name
        let line = if narrow {
            format!(
                "{}{} {} {}{}{}{}",
                prefix,
                pad_left(&idx_str, col_idx),
                pad_left(&agent.name, col_name),
                status_color,
                if needs_attention { BOLD } else { "" },
                pad_left(status_label, col_status),
                RESET,
            )
        } else {
            format!(
                "{}{} {} {}{}{}{} {} {}",
                prefix,
                pad_left(&idx_str, col_idx),
                pad_left(&agent.name, col_name),
                status_color,
                if needs_attention { BOLD } else { "" },
                pad_left(status_label, col_status),
                RESET,
                pad_left(profile_str, col_profile),
                pad_left(&agent.project_dir, col_project),
            )
        };

        if is_selected {
            // Selected row: full-width reverse video with colored status
            let main_before_status = if narrow {
                format!(
                    "{}{} {}",
                    prefix,
                    pad_left(&idx_str, col_idx),
                    pad_left(&agent.name, col_name),
                )
            } else {
                format!(
                    "{}{} {}",
                    prefix,
                    pad_left(&idx_str, col_idx),
                    pad_left(&agent.name, col_name),
                )
            };

            let status_str = pad_left(status_label, col_status);
            let after_status = if narrow {
                String::new()
            } else {
                format!(
                    " {} {}",
                    pad_left(profile_str, col_profile),
                    pad_left(&agent.project_dir, col_project),
                )
            };

            let plain_len = main_before_status.len() + 1 + status_str.len() + after_status.len();
            let fill = cols.saturating_sub(plain_len);

            print!(
                "{}{} {}{}{}{}{}{}{}{}",
                REVERSE,
                main_before_status,
                status_color,
                if needs_attention { BOLD } else { "" },
                REVERSE,
                status_str,
                RESET,
                REVERSE,
                after_status,
                RESET,
            );
            // Fill remaining width
            if fill > 0 {
                print!("{}{:>fill$}{}", REVERSE, "", RESET, fill = fill);
            }
            println!();
        } else {
            println!("{}", truncate(&line, cols));
        }
    }
}

fn render_command_bar(cols: usize, input_mode: bool, status_message: Option<&str>) {
    let text = if let Some(msg) = status_message {
        msg.to_string()
    } else if input_mode {
        "[INPUT MODE] Type to send to agent. [Esc] to exit".to_string()
    } else {
        "[n]ew  [f]ocus  [h]ide  [k]ill  [i]nput  [q]uit".to_string()
    };

    let display = truncate(&text, cols.saturating_sub(2));
    print!(
        "{} {:<width$}{}",
        REVERSE,
        display,
        RESET,
        width = cols.saturating_sub(1),
    );
    println!();
}
