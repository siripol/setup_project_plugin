"""Merge algebra for .claude/settings.json.

Each policy's settings.patch.json is applied with `apply_patch` and reversed
with `remove_policy`. Array entries must carry `policy: <slug>` markers;
dedup is by (matcher, policy) tuple. Object keys are deep-merged.
"""
from __future__ import annotations

import policy_errors


def _is_array_of_entries(val: object) -> bool:
    return isinstance(val, list) and all(isinstance(x, dict) for x in val)


def apply_patch(target: dict, patch: dict, expected_policy: str) -> dict:
    """Deep-merge `patch` into `target`. Mutates + returns `target`."""
    _merge(target, patch, expected_policy)
    return target


def _merge(target: dict, patch: dict, expected_policy: str) -> None:
    for key, val in patch.items():
        if isinstance(val, dict):
            sub = target.setdefault(key, {})
            if not isinstance(sub, dict):
                # Type mismatch — replace.
                target[key] = val
                continue
            _merge(sub, val, expected_policy)
        elif _is_array_of_entries(val):
            existing = target.setdefault(key, [])
            if not isinstance(existing, list):
                target[key] = val
                continue
            for entry in val:
                _check_policy_field(entry, expected_policy)
                _merge_array_entry(existing, entry)
        elif isinstance(val, list):
            existing = target.setdefault(key, [])
            if isinstance(existing, list):
                existing.extend(x for x in val if x not in existing)
            else:
                target[key] = val
        else:
            target[key] = val


def _check_policy_field(entry: dict, expected_policy: str) -> None:
    if "policy" not in entry:
        raise policy_errors.MalformedPatch(
            f"settings patch entry missing required 'policy' field: {entry}"
        )
    if entry["policy"] != expected_policy:
        raise policy_errors.MalformedPatch(
            f"settings patch entry has policy={entry['policy']!r} but the "
            f"patch is being applied for policy={expected_policy!r}"
        )


def _merge_array_entry(existing: list[dict], entry: dict) -> None:
    key = (entry.get("matcher"), entry["policy"])
    for i, other in enumerate(existing):
        other_key = (other.get("matcher"), other.get("policy"))
        if other_key == key:
            if other.get("version") != entry.get("version"):
                existing[i] = entry
            return
    existing.append(entry)


def remove_policy(target: dict, slug: str) -> dict:
    """Strip every array entry where policy == slug. Leaves empty arrays in place."""
    _strip(target, slug)
    return target


def _strip(node: dict, slug: str) -> None:
    for key, val in list(node.items()):
        if isinstance(val, dict):
            _strip(val, slug)
        elif _is_array_of_entries(val):
            node[key] = [e for e in val if e.get("policy") != slug]
