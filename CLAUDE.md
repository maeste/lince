# Claude Code on Linux — Dev Guidelines

## Project Structure
- `sandbox/` — Bubblewrap sandbox for Claude Code (Python 3.11+, single-file script)
- `voxcode/` — Voice coding assistant, STT (Python, uv-managed)
- `voxtts/` — Text-to-Speech with local engines (Python 3.12, uv-managed)
- `lince-dashboard/` — Multi-agent TUI dashboard (Zellij WASM plugin, Rust)

## Build / Test
- **sandbox**: No build step. `python3 sandbox/claude-sandbox --help` to verify.
- **voxcode**: `cd voxcode && uv sync && uv run voxcode --help`
- **voxtts**: `cd voxtts && uv sync && uv run voxtts --help`
- **lince-dashboard**: `cd lince-dashboard/plugin && PATH="$HOME/.cargo/bin:$PATH" cargo build --target wasm32-wasip1`

### Rust / WASM toolchain note
Fedora ships a system `rustc` at `/usr/bin/rustc` that **does not** include the `wasm32-wasip1` standard library. Always use the **rustup-managed** toolchain when building the dashboard plugin:
```bash
PATH="$HOME/.cargo/bin:$PATH" cargo build --target wasm32-wasip1
```
Or the build will fail with "can't find crate for `core`".

### WASI sandbox filesystem limitations
Zellij WASM plugins run inside a WASI sandbox with **restricted filesystem access**. `std::fs::read_to_string()` and similar direct I/O calls **silently fail** for paths outside the plugin's mapped directories (e.g. `~/.claude-sandbox/config.toml`).

**Rule**: All file I/O in the dashboard plugin must use `run_command()` (async shell commands via Zellij host) instead of `std::fs` calls. The result arrives in `Event::RunCommandResult` with a context map to identify the operation. See `state_file.rs` and `config.rs` `discover_profiles_async()` for the pattern.

## Installation Conventions

Every module must provide `install.sh`, `update.sh`, and `uninstall.sh` scripts.
- All file copies, config changes, and system modifications go through these scripts — never done manually or directly by Claude
- This applies to all modules: sandbox, voxcode, voxtts, lince-dashboard, and any future modules
- Scripts must be idempotent and safe to run multiple times
- The system must be installable by third parties from a clean clone

## Code Style
- Python: ruff defaults, line length 119
- Use absolute imports (never relative)
- Type hints where practical
- snake_case for functions/variables, CamelCase for classes

<!-- BACKLOG.MD MCP GUIDELINES START -->

<CRITICAL_INSTRUCTION>

## BACKLOG WORKFLOW INSTRUCTIONS

This project uses Backlog.md MCP for all task and project management activities.

**CRITICAL GUIDANCE**

- If your client supports MCP resources, read `backlog://workflow/overview` to understand when and how to use Backlog for this project.
- If your client only supports tools or the above request fails, call `backlog.get_workflow_overview()` tool to load the tool-oriented overview (it lists the matching guide tools).

- **First time working here?** Read the overview resource IMMEDIATELY to learn the workflow
- **Already familiar?** You should have the overview cached ("## Backlog.md Overview (MCP)")
- **When to read it**: BEFORE creating tasks, or when you're unsure whether to track work

These guides cover:
- Decision framework for when to create tasks
- Search-first workflow to avoid duplicates
- Links to detailed guides for task creation, execution, and finalization
- MCP tools reference

You MUST read the overview resource to understand the complete workflow. The information is NOT summarized here.

</CRITICAL_INSTRUCTION>

<!-- BACKLOG.MD MCP GUIDELINES END -->
