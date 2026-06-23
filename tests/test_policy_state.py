"""Tests for scripts/policy_state.py — state file migration + sha256 helpers."""
from __future__ import annotations

import json
from pathlib import Path

import policy_state  # type: ignore


def test_migrate_adds_empty_arrays_when_missing():
    state = {"sn_init_version": "0.1.0", "mode": "new"}
    migrated = policy_state.migrate(state)
    assert migrated["applied_policies"] == []
    assert migrated["policy_history"] == []


def test_migrate_idempotent_when_arrays_present():
    state = {"applied_policies": [{"slug": "x"}], "policy_history": [{"action": "apply"}]}
    migrated = policy_state.migrate(state)
    assert migrated["applied_policies"] == [{"slug": "x"}]
    assert migrated["policy_history"] == [{"action": "apply"}]


def test_read_state_runs_migration(tmp_path: Path):
    sp = tmp_path / ".sn-init-state.json"
    sp.write_text(json.dumps({"mode": "new"}))
    state = policy_state.read_state(tmp_path)
    assert state["applied_policies"] == []
    assert state["policy_history"] == []


def test_write_state_round_trips(tmp_path: Path):
    state = {"mode": "new", "applied_policies": [], "policy_history": []}
    policy_state.write_state(tmp_path, state)
    loaded = json.loads((tmp_path / ".sn-init-state.json").read_text())
    assert loaded == state


def test_write_state_is_atomic(tmp_path: Path):
    """Writer must use tmp+rename so a partial write never corrupts the file."""
    state = {"mode": "new"}
    policy_state.write_state(tmp_path, state)
    assert not (tmp_path / ".sn-init-state.json.tmp").exists()


def test_sha256_file(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("hello\n")
    h = policy_state.sha256_file(p)
    assert h == "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"


def test_sha256_str():
    assert policy_state.sha256_str("hello\n") == \
        "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"


def test_read_state_handles_empty_file(tmp_path: Path):
    """An empty/zero-byte state file (manual touch, or interrupted write)
    must not crash with JSONDecodeError — migrate returns empty arrays."""
    (tmp_path / ".sn-init-state.json").write_text("")
    state = policy_state.read_state(tmp_path)
    assert state["applied_policies"] == []
    assert state["policy_history"] == []
