"""Tests for scripts/policy_settings_merge.py."""
from __future__ import annotations

import pytest

import policy_errors  # type: ignore
import policy_settings_merge as sm  # type: ignore


def test_apply_patch_appends_into_empty_target():
    target: dict = {"hooks": {}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}
    sm.apply_patch(target, patch, expected_policy="p1")
    assert target == {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}


def test_apply_patch_appends_distinct_matcher():
    target = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "a.sh"}
    ]}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "p2", "version": "1.0.0", "matcher": "Edit", "command": "b.sh"}
    ]}}
    sm.apply_patch(target, patch, expected_policy="p2")
    assert len(target["hooks"]["PreToolUse"]) == 2


def test_apply_patch_dedupes_same_matcher_same_policy_same_version():
    base = {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "a.sh"}
    target = {"hooks": {"PreToolUse": [base.copy()]}}
    sm.apply_patch(target, {"hooks": {"PreToolUse": [base.copy()]}}, expected_policy="p1")
    assert len(target["hooks"]["PreToolUse"]) == 1


def test_apply_patch_replaces_on_version_change():
    target = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "old.sh"}
    ]}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.1.0", "matcher": "Write", "command": "new.sh"}
    ]}}
    sm.apply_patch(target, patch, expected_policy="p1")
    assert target["hooks"]["PreToolUse"] == [
        {"policy": "p1", "version": "1.1.0", "matcher": "Write", "command": "new.sh"}
    ]


def test_apply_patch_rejects_entry_without_policy_field():
    target: dict = {"hooks": {}}
    patch = {"hooks": {"PreToolUse": [
        {"version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}
    with pytest.raises(policy_errors.MalformedPatch):
        sm.apply_patch(target, patch, expected_policy="p1")


def test_apply_patch_rejects_entry_with_wrong_policy_field():
    target: dict = {"hooks": {}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "wrong-slug", "version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}
    with pytest.raises(policy_errors.MalformedPatch):
        sm.apply_patch(target, patch, expected_policy="p1")


def test_remove_policy_strips_matching_entries_only():
    target = {"hooks": {
        "PreToolUse": [
            {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "a.sh"},
            {"policy": "p2", "version": "1.0.0", "matcher": "Edit", "command": "b.sh"},
        ],
        "PreCommit": [
            {"policy": "p1", "version": "1.0.0", "command": "c.sh"},
        ],
    }}
    sm.remove_policy(target, "p1")
    assert target["hooks"]["PreToolUse"] == [
        {"policy": "p2", "version": "1.0.0", "matcher": "Edit", "command": "b.sh"}
    ]
    assert target["hooks"]["PreCommit"] == []  # emptied, not deleted


def test_apply_patch_deep_merges_object_keys():
    target = {"permissions": {"allow": ["Read"]}}
    patch = {"permissions": {"allow": ["Write"], "deny": ["Bash"]}}
    sm.apply_patch(target, patch, expected_policy="p1")
    assert target["permissions"] == {"allow": ["Read", "Write"], "deny": ["Bash"]}
