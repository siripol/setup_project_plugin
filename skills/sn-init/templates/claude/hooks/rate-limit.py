"""PreToolUse rate-limit hook for the Claude Agent SDK (Python).

Caps (env):
  SN_MAX_CALLS_PER_HOUR  = 200
  SN_MAX_TOKENS_PER_HOUR = 2_000_000

Returns `{"action": "block"}` (or equivalent) when limits are exceeded.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_CALLS = int(os.environ.get("SN_MAX_CALLS_PER_HOUR", "200"))
MAX_TOKENS = int(os.environ.get("SN_MAX_TOKENS_PER_HOUR", "2000000"))


def _project_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    while p != p.parent:
        if (p / ".sn-init").exists() or (p / "CLAUDE.md").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


def _load_state() -> dict:
    state_path = _project_root() / ".sn-init" / "workflow-state.json"
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    state_path = _project_root() / ".sn-init" / "workflow-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _current_window(now: datetime) -> tuple[int, int]:
    state = _load_state()
    window = state.get("rate_window", {})
    started = window.get("window_start")
    calls = int(window.get("calls_this_hour", 0))
    tokens = int(window.get("tokens_this_hour", 0))
    if started:
        try:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            if (now - start_dt).total_seconds() > 3600:
                return 0, 0
        except Exception:
            return 0, 0
    return calls, tokens


def _record_call(input_data: dict) -> None:
    now = datetime.now(timezone.utc)
    state = _load_state()
    window = state.setdefault("rate_window", {})
    started = window.get("window_start")
    started_dt = None
    if started:
        try:
            started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        except Exception:
            started_dt = None
    if started_dt is None or (now - started_dt).total_seconds() > 3600:
        window["window_start"] = now.isoformat()
        window["calls_this_hour"] = 0
        window["tokens_this_hour"] = 0
    window["calls_this_hour"] = int(window.get("calls_this_hour", 0)) + 1
    usage = (input_data or {}).get("usage") or {}
    window["tokens_this_hour"] = (
        int(window.get("tokens_this_hour", 0))
        + int(usage.get("input_tokens", 0))
        + int(usage.get("output_tokens", 0))
    )
    _save_state(state)


async def rate_limit_hook(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    """Block when this hour's quota is exceeded."""
    now = datetime.now(timezone.utc)
    calls, tokens = _current_window(now)
    if calls >= MAX_CALLS or tokens >= MAX_TOKENS:
        return {
            "action": "block",
            "reason": (
                f"sn-init rate limit: {calls}/{MAX_CALLS} calls, {tokens}/{MAX_TOKENS} tokens "
                "this hour. Wait or raise SN_MAX_*_PER_HOUR."
            ),
        }
    _record_call(input_data)
    return {}
