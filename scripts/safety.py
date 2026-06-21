"""Safety state helpers for sn-init scaffolded projects.

Manages `.sn-init/workflow-state.json` fields used by:
- rate-limit hook (`rate_window` block)
- circuit breaker (`progress_history`, `repeat_error_count`, `circuit_breaker_state`,
  `cooldown_until`)

Importable from scaffolded code or invoked as a CLI for one-off ops:

    python3 scripts/safety.py status
    python3 scripts/safety.py reset-rate-limit
    python3 scripts/safety.py trip-breaker REQ-NNN
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_COOLDOWN_MINUTES = 5
NO_PROGRESS_THRESHOLD = 3       # 3 cycles w/o eval improvement → pause
REPEAT_ERROR_THRESHOLD = 5      # 5 cycles same failing test → rollback


def _project_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    while p != p.parent:
        if (p / ".sn-init").exists() or (p / "CLAUDE.md").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


def state_path() -> Path:
    return _project_root() / ".sn-init" / "workflow-state.json"


def load() -> dict:
    p = state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(state: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# --- rate window ---


def reset_rate_window(state: dict | None = None) -> dict:
    state = state if state is not None else load()
    state["rate_window"] = {
        "window_start": datetime.now(timezone.utc).isoformat(),
        "calls_this_hour": 0,
        "tokens_this_hour": 0,
    }
    save(state)
    return state


def record_call(input_tokens: int = 0, output_tokens: int = 0) -> dict:
    state = load()
    window = state.get("rate_window") or {}
    started = window.get("window_start")
    started_dt: datetime | None = None
    if started:
        try:
            started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        except Exception:
            started_dt = None
    now = datetime.now(timezone.utc)
    if started_dt is None or (now - started_dt).total_seconds() > 3600:
        window = {"window_start": now.isoformat(), "calls_this_hour": 0, "tokens_this_hour": 0}
    window["calls_this_hour"] = int(window.get("calls_this_hour", 0)) + 1
    window["tokens_this_hour"] = (
        int(window.get("tokens_this_hour", 0)) + int(input_tokens) + int(output_tokens)
    )
    state["rate_window"] = window
    save(state)
    return window


# --- circuit breaker ---


def record_progress(req_id: str, eval_score: int | None) -> dict:
    """Append eval_score to per-REQ progress history. Trips breaker on stall."""
    state = load()
    history = state.setdefault("progress_history", {}).setdefault(req_id, [])
    if eval_score is not None:
        history.append(int(eval_score))
    breaker = state.setdefault("circuit_breaker_state", {})
    breaker.setdefault(req_id, "closed")
    if len(history) >= NO_PROGRESS_THRESHOLD:
        recent = history[-NO_PROGRESS_THRESHOLD:]
        # No improvement = max stays the same across N cycles.
        if max(recent) <= recent[0]:
            breaker[req_id] = "tripped"
            state.setdefault("cooldown_until", {})[req_id] = (
                datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_COOLDOWN_MINUTES)
            ).isoformat()
    save(state)
    return state


def record_repeat_error(req_id: str, signature: str) -> dict:
    state = load()
    counts = state.setdefault("repeat_error_count", {}).setdefault(req_id, {})
    counts[signature] = int(counts.get(signature, 0)) + 1
    if counts[signature] >= REPEAT_ERROR_THRESHOLD:
        state.setdefault("circuit_breaker_state", {})[req_id] = "tripped"
    save(state)
    return state


def breaker_status(req_id: str) -> str:
    state = load()
    return state.get("circuit_breaker_state", {}).get(req_id, "closed")


def is_in_cooldown(req_id: str) -> bool:
    state = load()
    until = state.get("cooldown_until", {}).get(req_id)
    if not until:
        return False
    try:
        dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
    except Exception:
        return False
    return datetime.now(timezone.utc) < dt


def reset_breaker(req_id: str) -> dict:
    state = load()
    state.setdefault("circuit_breaker_state", {})[req_id] = "closed"
    state.setdefault("cooldown_until", {}).pop(req_id, None)
    save(state)
    return state


# --- CLI ---


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: safety.py status | reset-rate-limit | trip-breaker REQ | reset-breaker REQ"
        )
        return 0
    cmd = argv[0]
    if cmd == "status":
        state = load()
        print(json.dumps({
            "rate_window": state.get("rate_window", {}),
            "circuit_breaker_state": state.get("circuit_breaker_state", {}),
            "cooldown_until": state.get("cooldown_until", {}),
        }, indent=2))
        return 0
    if cmd == "reset-rate-limit":
        reset_rate_window()
        print("rate window reset")
        return 0
    if cmd == "trip-breaker":
        if len(argv) < 2:
            print("usage: safety.py trip-breaker REQ-NNN", file=sys.stderr)
            return 2
        state = load()
        state.setdefault("circuit_breaker_state", {})[argv[1]] = "tripped"
        state.setdefault("cooldown_until", {})[argv[1]] = (
            datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_COOLDOWN_MINUTES)
        ).isoformat()
        save(state)
        print(f"breaker tripped for {argv[1]}")
        return 0
    if cmd == "reset-breaker":
        if len(argv) < 2:
            print("usage: safety.py reset-breaker REQ-NNN", file=sys.stderr)
            return 2
        reset_breaker(argv[1])
        print(f"breaker reset for {argv[1]}")
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
