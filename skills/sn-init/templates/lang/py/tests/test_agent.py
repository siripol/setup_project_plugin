"""Smoke test placeholder for src/agent.py."""
from __future__ import annotations

import importlib


def test_agent_module_imports():
    mod = importlib.import_module("agent")
    assert hasattr(mod, "main"), "agent.main coroutine missing"
