#!/usr/bin/env python3
"""Append selected sandbox-level agent blocks from agents-template.toml
into the user's lince-dashboard config.toml.

Usage: apply-sandbox-levels.py <template> <user_config> <levels_csv>

Per-agent feature support is implicit: only `[agents.<agent>-<level>]`
blocks present in <template> are applied. Already-present blocks in
<user_config> are skipped (idempotent across re-runs).

Prints one `agent-level` per line for each block actually appended.
"""

import re
import sys
from pathlib import Path


SECTION_RE = re.compile(r"(?m)^(\[agents\.[^\]]+\])\s*$")


def split_sections(text: str) -> dict[str, str]:
    """Map [agents.X] header → that section's text (header through to the
    char before the next [agents.*] header or EOF), preserving comments."""
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[m.group(1)] = text[m.start():end].rstrip() + "\n"
    return sections


def has_section(cfg_text: str, agent_name: str) -> bool:
    pattern = rf"^\[agents\.{re.escape(agent_name)}\]\s*$"
    return re.search(pattern, cfg_text, re.M) is not None


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2

    template_path = Path(argv[1])
    cfg_path = Path(argv[2])
    levels = [
        level.strip()
        for level in argv[3].split(",")
        if level.strip() and level.strip() != "normal"
    ]

    if not levels:
        return 0

    template_text = template_path.read_text()
    sections = split_sections(template_text)

    cfg_text = cfg_path.read_text() if cfg_path.exists() else ""

    added: list[str] = []
    for level in levels:
        head_re = re.compile(rf"^\[agents\.([\w-]+)-{re.escape(level)}\]\s*$", re.M)
        for hm in head_re.finditer(template_text):
            agent_name = f"{hm.group(1)}-{level}"
            if has_section(cfg_text, agent_name):
                continue
            block = sections.get(f"[agents.{agent_name}]", "")
            env_block = sections.get(f"[agents.{agent_name}.env_vars]", "")
            if not block:
                continue
            cfg_text = cfg_text.rstrip() + "\n\n" + block
            if env_block:
                cfg_text = cfg_text.rstrip() + "\n\n" + env_block
            added.append(agent_name)

    if added:
        cfg_path.write_text(cfg_text + ("\n" if not cfg_text.endswith("\n") else ""))
    print("\n".join(added))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
