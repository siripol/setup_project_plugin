#!/usr/bin/env python3
"""Verify src/agent.{py,ts,go} against the 6 mechanically-checkable Agent SDK
best-practices rules.

Rules referenced by number from docs/principles/agent-sdk-best-practices.md:

    1. Whitelist tools (`allowed_tools=[...]` / `allowedTools: [...]`)
    2. No hardcoded ANTHROPIC_API_KEY literal
    3. Pinned model id (`model="..."`)
    5. Hooks present (`HookMatcher(...)` / `hooks:` block)
    6. Subagent definitions with non-empty `tools=[...]`
    9. `setting_sources=["project"]` / `settingSources: ["project"]`
       (only checked when .sn-init-state.json records `tier in {3, "both"}`)

Exit codes:
    0   every applicable rule passes for every agent file.
    2   at least one rule failed. Each failure printed as
        `::error file=<path>::rule N: <description>` so GitHub Actions
        surfaces it inline.
    3   no `src/agent.*` files found — the scaffold may be Tier 1 only.

Usage:
    python3 scripts/verify_agent_sdk.py
    make verify
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


AGENT_FILE_GLOBS = ("src/agent.py", "src/agent.ts", "src/agent.go", "src/cmd/orchestrator/main.go")


def _agent_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for glob in AGENT_FILE_GLOBS:
        for p in root.glob(glob):
            if p.is_file():
                out.append(p)
    return sorted(out)


def _is_tier3(state_path: Path) -> bool:
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    tier = str(state.get("tier", "both"))
    return tier in ("3", "both")


def _emit(path: Path, root: Path, rule: int, message: str) -> None:
    rel = path.relative_to(root)
    print(f"::error file={rel}::rule {rule}: {message}", file=sys.stderr)


def _check_python(path: Path, root: Path, tier3: bool) -> int:
    fails = 0
    text = path.read_text(encoding="utf-8")
    if "allowed_tools" not in text:
        _emit(path, root, 1, "no `allowed_tools=[...]` whitelist found")
        fails += 1
    # Rule 2 — flag any literal that looks like an embedded key. We allow the
    # token to appear in env-var lookups (`os.environ["ANTHROPIC_API_KEY"]`)
    # but block string assignments.
    if re.search(r'ANTHROPIC_API_KEY\s*=\s*["\']sk-', text) or re.search(
        r'["\']sk-[A-Za-z0-9_-]{20,}["\']', text
    ):
        _emit(path, root, 2, "hardcoded API key literal detected")
        fails += 1
    if not re.search(r'\bmodel\s*=\s*["\']', text):
        _emit(path, root, 3, 'no `model="..."` keyword arg; SDK default is unstable')
        fails += 1
    if "HookMatcher" not in text and "hooks=" not in text and "hooks={" not in text:
        _emit(path, root, 5, "no HookMatcher or `hooks=` block; guaranteed side effects belong in hooks")
        fails += 1
    if "AgentDefinition" in text and not re.search(r"AgentDefinition\([^)]*tools\s*=", text, re.S):
        _emit(path, root, 6, "AgentDefinition without non-empty `tools=[...]` whitelist")
        fails += 1
    if tier3 and 'setting_sources' not in text:
        _emit(path, root, 9, 'tier 3 production scaffold but no `setting_sources=["project"]` restriction')
        fails += 1
    return fails


def _check_typescript(path: Path, root: Path, tier3: bool) -> int:
    fails = 0
    text = path.read_text(encoding="utf-8")
    if "allowedTools" not in text:
        _emit(path, root, 1, "no `allowedTools: [...]` whitelist found")
        fails += 1
    if re.search(r'ANTHROPIC_API_KEY\s*=\s*["\']sk-', text) or re.search(
        r'["\']sk-[A-Za-z0-9_-]{20,}["\']', text
    ):
        _emit(path, root, 2, "hardcoded API key literal detected")
        fails += 1
    if not re.search(r'\bmodel\s*:\s*["\']', text):
        _emit(path, root, 3, 'no `model: "..."` field; SDK default is unstable')
        fails += 1
    if "hooks:" not in text and "hooks =" not in text:
        _emit(path, root, 5, "no `hooks:` block; guaranteed side effects belong in hooks")
        fails += 1
    if tier3 and "settingSources" not in text:
        _emit(path, root, 9, 'tier 3 production scaffold but no `settingSources: ["project"]` restriction')
        fails += 1
    return fails


def _check_go(path: Path, root: Path, _tier3: bool) -> int:
    # Go SDK uses the Anthropic Go SDK directly — most of the rules are
    # Python/TS-shaped. Only rule 2 (no hardcoded key) is meaningful.
    fails = 0
    text = path.read_text(encoding="utf-8")
    if re.search(r'"sk-[A-Za-z0-9_-]{20,}"', text):
        _emit(path, root, 2, "hardcoded API key literal detected")
        fails += 1
    return fails


def main(argv: list[str] | None = None) -> int:
    root = Path.cwd()
    files = _agent_files(root)
    if not files:
        print("verify_agent_sdk: no src/agent.{py,ts,go} files found.", file=sys.stderr)
        return 3
    tier3 = _is_tier3(root / ".sn-init-state.json")
    fails = 0
    for path in files:
        suffix = path.suffix
        if suffix == ".py":
            fails += _check_python(path, root, tier3)
        elif suffix == ".ts":
            fails += _check_typescript(path, root, tier3)
        elif suffix == ".go":
            fails += _check_go(path, root, tier3)
    if fails:
        print(f"verify_agent_sdk: {fails} rule failure(s) across {len(files)} file(s)", file=sys.stderr)
        return 2
    print(f"verify_agent_sdk: {len(files)} file(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
