"""Tier 2 — local agent loop via claude-agent-sdk.

Runnable stub. Run with `make agent-run` or `uv run src/agent.py`.
"""
from __future__ import annotations

import asyncio
import os

from claude_agent_sdk import (
    ClaudeAgentOptions,
    AgentDefinition,
    query,
)


async def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("set ANTHROPIC_API_KEY in env")

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Agent"],
        agents={
            "code-reviewer": AgentDefinition(
                description="Reviews code for bugs, style, and security.",
                prompt="Analyze code quality and suggest improvements.",
                tools=["Read", "Glob", "Grep"],
            )
        },
    )

    prompt = "List the files in this directory and summarize the project layout."
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "result"):
            print(message.result)


if __name__ == "__main__":
    asyncio.run(main())
