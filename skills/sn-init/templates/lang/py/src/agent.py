"""Tier 2 — local agent loop via claude-agent-sdk.

Runnable stub. Run with `make agent-run` or `uv run src/agent.py`.
"""
from __future__ import annotations

import asyncio
import os

import sys
from pathlib import Path

# Make the .claude/hooks audit module importable.
_HOOKS = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
if _HOOKS.exists() and str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from claude_agent_sdk import (  # noqa: E402
    ClaudeAgentOptions,
    AgentDefinition,
    HookMatcher,
    query,
)

try:
    from audit import audit_hook  # type: ignore
except ImportError:
    audit_hook = None  # audit hook disabled


async def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("set ANTHROPIC_API_KEY in env")

    hooks = {}
    if audit_hook is not None:
        hooks = {
            "PreToolUse":       [HookMatcher(matcher=".*", hooks=[audit_hook])],
            "PostToolUse":      [HookMatcher(matcher=".*", hooks=[audit_hook])],
            "UserPromptSubmit": [HookMatcher(matcher=".*", hooks=[audit_hook])],
            "Stop":             [HookMatcher(matcher=".*", hooks=[audit_hook])],
        }

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Agent"],
        agents={
            "code-reviewer": AgentDefinition(
                description="Reviews code for bugs, style, and security.",
                prompt="Analyze code quality and suggest improvements.",
                tools=["Read", "Glob", "Grep"],
            )
        },
        hooks=hooks,
    )

    prompt = "List the files in this directory and summarize the project layout."
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "result"):
            print(message.result)


if __name__ == "__main__":
    asyncio.run(main())
