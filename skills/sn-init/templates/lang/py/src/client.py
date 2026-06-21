"""Tier 3 — Managed Agents session driver via anthropic SDK.

Stubs `client.beta.sessions.create`. Replace placeholder logic with the real
event-stream consumer for your use case.
"""
from __future__ import annotations

import os
from typing import Optional


def run_session(agent_id: Optional[str] = None) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("set ANTHROPIC_API_KEY in env")
    agent_id = agent_id or os.environ.get("AGENT_ID")
    if not agent_id:
        raise SystemExit("set AGENT_ID or pass it to run_session()")

    # Pseudocode (uncomment after `make install`):
    #
    #   from anthropic import Anthropic
    #   client = Anthropic()
    #   session = client.beta.sessions.create(agent_id=agent_id)
    #   for event in client.beta.sessions.events.stream(session.id):
    #       print(event)
    print(f"client.py stub — would create Managed Agent session for agent {agent_id}")


if __name__ == "__main__":
    run_session()
