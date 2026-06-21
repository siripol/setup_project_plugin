"""PreToolUse chokepoint-gate hook for the Claude Agent SDK (Python).

Reads `.harness/chokepoints.yaml` and blocks Edit/Write/etc. calls targeting
any listed file or glob. Use to keep agents off load-bearing files until a
human OKs the change.
"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any


def _project_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    while p != p.parent:
        if (p / ".sn-init").exists() or (p / "CLAUDE.md").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


def _patterns() -> list[str]:
    root = _project_root()
    path = root / ".harness" / "chokepoints.yaml"
    if not path.exists():
        return []
    items: list[str] = []
    in_block = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\s*chokepoints\s*:\s*$", line):
            in_block = True
            continue
        if in_block:
            m = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if m:
                items.append(m.group(1))
            elif line.strip() and not line.lstrip().startswith("#"):
                # next top-level key terminates the block
                break
    return items


def _target_path(input_data: dict) -> str | None:
    ti = (input_data or {}).get("tool_input") or {}
    for key in ("file_path", "path", "target"):
        val = ti.get(key)
        if isinstance(val, str) and val:
            return val
    return None


async def chokepoint_gate_hook(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    target = _target_path(input_data)
    if target is None:
        return {}

    root = _project_root()
    try:
        relative = str(Path(target).resolve().relative_to(root))
    except ValueError:
        relative = target

    for pat in _patterns():
        if fnmatch.fnmatch(relative, pat):
            return {
                "action": "block",
                "reason": (
                    f"chokepoint-gate: '{relative}' matches '{pat}'. "
                    "Edit this file only after a human approves the change."
                ),
            }
    return {}
