"""Tier 2 — local agent loop via claude-agent-sdk.

Runs a Read/Glob/Grep agent against the current project directory and
delegates the heavy review pass to the `code-reviewer` subagent.

Run with `make agent-run` (uv) or `uv run python src/agent.py`.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Make the .claude/hooks audit + safety modules importable.
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
    audit_hook = None

try:
    from rate_limit import rate_limit_hook  # type: ignore
except ImportError:
    rate_limit_hook = None

try:
    from chokepoint_gate import chokepoint_gate_hook  # type: ignore
except ImportError:
    chokepoint_gate_hook = None


DEFAULT_PROMPT = (
    "Summarize this project's structure: read AGENTS.md and the top-level "
    "files; report owners, key invariants, and any obvious risks."
)


def _hook_block():
    pre = []
    if rate_limit_hook is not None:
        pre.append(HookMatcher(matcher=".*", hooks=[rate_limit_hook]))
    if chokepoint_gate_hook is not None:
        pre.append(HookMatcher(matcher="Edit|Write", hooks=[chokepoint_gate_hook]))
    if audit_hook is not None:
        pre.append(HookMatcher(matcher=".*", hooks=[audit_hook]))
    post = (
        [HookMatcher(matcher=".*", hooks=[audit_hook])] if audit_hook is not None else []
    )
    standalone = [HookMatcher(matcher=".*", hooks=[audit_hook])] if audit_hook is not None else []
    hooks = {}
    if pre:
        hooks["PreToolUse"] = pre
    if post:
        hooks["PostToolUse"] = post
    if standalone:
        hooks["UserPromptSubmit"] = standalone
        hooks["Stop"] = standalone
    return hooks


async def run_agent(prompt: str = DEFAULT_PROMPT) -> list[object]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("set ANTHROPIC_API_KEY in env")

    options = ClaudeAgentOptions(
        # Rule 3 — pin the model id; SDK default is a moving target.
        model="${model}",
        allowed_tools=["Read", "Glob", "Grep", "Agent"],
        agents={
            "code-reviewer": AgentDefinition(
                description="Reviews code for bugs, style, and security.",
                prompt="Analyze code quality and suggest improvements.",
                tools=["Read", "Glob", "Grep"],
            )
        },
        hooks=_hook_block(),
        # Rule 9 — production scaffolds restrict the config load surface
        # so a developer-local `~/.claude/` override cannot leak in.
        setting_sources=["project"],
    )

    captured: list[object] = []
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "result"):
            captured.append(message.result)
            print(message.result)
    return captured


async def main() -> None:
    prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT
    await run_agent(prompt)


if __name__ == "__main__":
    asyncio.run(main())
