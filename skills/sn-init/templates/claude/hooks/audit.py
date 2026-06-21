"""Audit hook for the Claude Agent SDK (Python).

Wire via:

    from claude_agent_sdk import ClaudeAgentOptions, HookMatcher
    from .audit import audit_hook

    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [HookMatcher(matcher=".*", hooks=[audit_hook])],
            "PostToolUse": [HookMatcher(matcher=".*", hooks=[audit_hook])],
            "UserPromptSubmit": [HookMatcher(matcher=".*", hooks=[audit_hook])],
            "Stop": [HookMatcher(matcher=".*", hooks=[audit_hook])],
        }
    )

Writes one JSONL record per event to `.sn-init/logs/exec-<date>-<session>.jsonl`.
Truncates `tool_output` over 2KB and spills the full payload to `.sn-init/logs/blobs/<hash>.txt`.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_INLINE_BYTES = 2048


def _project_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    while p != p.parent:
        if (p / ".sn-init").exists() or (p / "CLAUDE.md").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


def _log_paths(session_id: str) -> tuple[Path, Path]:
    root = _project_root()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_dir = root / ".sn-init" / "logs"
    blob_dir = log_dir / "blobs"
    log_dir.mkdir(parents=True, exist_ok=True)
    blob_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"exec-{date}-{session_id}.jsonl", blob_dir


def _truncate(value: Any) -> tuple[Any, bool, str | None]:
    """Return (inline_value, truncated, blob_hash)."""
    serialized = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    raw = serialized.encode("utf-8")
    if len(raw) <= MAX_INLINE_BYTES:
        return value, False, None
    blob_hash = hashlib.sha256(raw).hexdigest()[:16]
    _, blob_dir = _log_paths("blob-spill")  # ensure dirs exist
    (blob_dir / f"{blob_hash}.txt").write_bytes(raw)
    return serialized[:MAX_INLINE_BYTES], True, blob_hash


async def audit_hook(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    """Agent SDK hook signature: (input_data, tool_use_id, context) -> dict."""
    session_id = (
        getattr(context, "session_id", None)
        or os.environ.get("CLAUDE_SESSION_ID", "unknown")
    )
    log_path, _ = _log_paths(session_id)

    event = input_data.get("hook_event_name") or input_data.get("event") or "tool"
    tool_name = input_data.get("tool_name") or input_data.get("tool", {}).get("name")
    tool_input = input_data.get("tool_input")
    tool_output = input_data.get("tool_output") or input_data.get("output")

    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event": event,
        "tool_name": tool_name,
        "model": input_data.get("model"),
        "usage": input_data.get("usage"),
        "obsidian_backend": None,  # set by the orchestrator when applicable
    }

    if tool_use_id:
        record["tool_use_id"] = tool_use_id

    if tool_input is not None:
        record["tool_input"] = tool_input

    if tool_output is not None:
        inline, truncated, blob = _truncate(tool_output)
        record["tool_output"] = inline
        if truncated:
            record["truncated"] = True
            record["blob"] = blob

    try:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass  # never block the session

    return {}
