"""State-file helpers for the policy catalog.

Owns the read/write of `.sn-init-state.json` for everything under
`applied_policies` + `policy_history`. Atomic writes (tmp+rename) match the
pattern in `scripts/sn_init.py`. Migration silently adds the new arrays to
state files written by older sn-setup versions.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

STATE_FILENAME = ".sn-init-state.json"


def migrate(state: dict) -> dict:
    """Add policy-catalog arrays to a state dict if absent. Mutates + returns."""
    state.setdefault("applied_policies", [])
    state.setdefault("policy_history", [])
    return state


def read_state(target: Path) -> dict:
    """Read state file at `target / .sn-init-state.json`, migrate, return."""
    path = target / STATE_FILENAME
    if not path.exists():
        return migrate({})
    state = json.loads(path.read_text(encoding="utf-8"))
    return migrate(state)


def write_state(target: Path, state: dict) -> None:
    """Atomic write: tmp file + rename, so a partial write never corrupts."""
    path = target / STATE_FILENAME
    tmp = path.with_suffix(f".json.tmp-{secrets.token_hex(4)}")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    """sha256 hex of the file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_str(s: str) -> str:
    """sha256 hex of an arbitrary string (UTF-8)."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
