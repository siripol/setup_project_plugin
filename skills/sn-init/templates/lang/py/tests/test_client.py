"""Smoke test placeholder for src/client.py."""
from __future__ import annotations

import importlib


def test_client_module_imports():
    mod = importlib.import_module("client")
    assert hasattr(mod, "run_session"), "client.run_session function missing"
