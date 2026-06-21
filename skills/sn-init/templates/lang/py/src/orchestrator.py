"""Tier-2 spec-loop orchestrator wrapper.

Wires the language-agnostic state machine in ``scripts/orchestrator.py`` to
the Claude Agent SDK so each phase actually calls a subagent.

Run with: `uv run python src/orchestrator.py SPRINT-NNN`
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Reuse the project-local state machine.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import orchestrator as core  # type: ignore  # noqa: E402

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition  # type: ignore
except ImportError:
    query = None  # type: ignore
    ClaudeAgentOptions = None  # type: ignore
    AgentDefinition = None  # type: ignore


def _build_options(subagent: str) -> "ClaudeAgentOptions":
    return ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Edit", "Write", "Bash", "Agent"],
        agents={
            subagent: AgentDefinition(
                description=f"Spec-loop {subagent} phase",
                prompt=f"You are the {subagent} subagent. Follow your manifest under .claude/agents/{subagent}.md.",
                tools=["Read", "Glob", "Grep"],
            )
        },
    )


async def _invoke(subagent: str, prompt: str) -> dict:
    if query is None:
        return {"status": "ok", "note": "claude-agent-sdk not installed; stub call"}
    output = []
    async for message in query(prompt=prompt, options=_build_options(subagent)):
        if hasattr(message, "result"):
            output.append(message.result)
    verdict: dict = {"status": "ok", "subagent": subagent}
    if subagent == "evaluator" and output:
        # Evaluator returns a JSON verdict on the last message — best-effort parse.
        import json as _json
        try:
            verdict.update(_json.loads(output[-1]))
        except Exception:
            verdict["raw"] = output[-1]
    return verdict


def invoke_subagent(subagent: str, prompt: str, context: dict) -> dict:
    return asyncio.run(_invoke(subagent, prompt))


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: src/orchestrator.py SPRINT-NNN", file=sys.stderr)
        return 2

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("warning: ANTHROPIC_API_KEY not set; subagent calls will stub", file=sys.stderr)

    core.invoke_subagent = invoke_subagent  # type: ignore[assignment]
    return core.Orchestrator(sprint_id=args[0], project_root=Path.cwd()).run()


if __name__ == "__main__":
    raise SystemExit(main())
