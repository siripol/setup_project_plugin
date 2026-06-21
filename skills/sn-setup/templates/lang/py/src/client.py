"""Tier 3 — Managed Agents session driver via the anthropic SDK.

Creates a session against a previously-applied Managed Agent and streams
the resulting events. Reads AGENT_ID from env or argv.

Run with `make client-run` (uv) or `uv run python src/client.py`.
"""
from __future__ import annotations

import os
import sys
from typing import Optional


def run_session(agent_id: Optional[str] = None, message: str = "Hello from sn-init.") -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("set ANTHROPIC_API_KEY in env")
    agent_id = agent_id or os.environ.get("AGENT_ID")
    if not agent_id:
        raise SystemExit("set AGENT_ID or pass it to run_session()")

    try:
        from anthropic import Anthropic  # type: ignore
    except ImportError:
        print("anthropic SDK not installed. Run `make install` first.")
        return 1

    client = Anthropic()
    session = client.beta.sessions.create(agent_id=agent_id)
    print(f"session: {session.id}")

    client.beta.sessions.messages.create(
        session_id=session.id,
        content=message,
    )

    for event in client.beta.sessions.events.stream(session.id):
        # Each event is provider-typed; print the JSON serialisable repr.
        print(event)
        if getattr(event, "type", "") == "session.idle":
            break
    return 0


def main() -> int:
    msg = " ".join(sys.argv[1:]) or "Hello from sn-init."
    return run_session(message=msg)


if __name__ == "__main__":
    raise SystemExit(main())
