"""`sn-setup policy pdpa allowlist <verb>` sub-sub-command.

Manages the project-local PDPA scan exemption list at
`.claude/config/pdpa-allowlist.yaml`. Hand-edits are valid YAML; this CLI
adds validation (no directory traversal, no absolute paths, dedup).
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

import yaml

import policy_errors


ALLOWLIST_REL = Path(".claude") / "config" / "pdpa-allowlist.yaml"
SEEDED_HEADER = (
    "# Project-scoped PDPA scan exemptions.\n"
    "# Managed via: sn-setup policy pdpa allowlist {list|add|remove|explain}.\n"
    "# Hand-edits OK but the command validates globs.\n"
)


def _allowlist_path() -> Path:
    return Path.cwd() / ALLOWLIST_REL


def _load_globs(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("allowlist") or [])


def _write_globs(path: Path, globs: list[str]) -> None:
    body = SEEDED_HEADER + "allowlist:\n"
    for g in globs:
        body += f"  - \"{g}\"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _validate_glob(glob: str) -> None:
    if "../" in glob or glob.startswith("../"):
        raise policy_errors.PolicyError(
            "allowlist glob rejected: directory traversal forbidden"
        )
    if glob.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", glob):
        raise policy_errors.PolicyError(
            "allowlist glob rejected: use repo-relative globs only"
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sn-setup policy pdpa")
    sub = parser.add_subparsers(dest="cmd", required=True)

    al = sub.add_parser("allowlist")
    al_sub = al.add_subparsers(dest="verb", required=True)
    al_sub.add_parser("list")
    sp_add = al_sub.add_parser("add"); sp_add.add_argument("glob")
    sp_rm = al_sub.add_parser("remove"); sp_rm.add_argument("glob")
    sp_ex = al_sub.add_parser("explain"); sp_ex.add_argument("path")

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0

    if ns.cmd != "allowlist":
        return 2

    path = _allowlist_path()

    if ns.verb == "list":
        if not path.exists():
            print(
                f"sn-setup policy pdpa: PDPA allowlist not initialized at {path}.",
                file=sys.stderr,
            )
            return 2
        for g in _load_globs(path):
            print(g)
        return 0

    if ns.verb == "add":
        try:
            _validate_glob(ns.glob)
        except policy_errors.PolicyError as e:
            print(f"sn-setup policy pdpa: {e}", file=sys.stderr)
            return 2
        globs = _load_globs(path) if path.exists() else []
        if ns.glob in globs:
            return 0  # idempotent
        globs.append(ns.glob)
        _write_globs(path, globs)
        return 0

    if ns.verb == "remove":
        if not path.exists():
            print(
                f"sn-setup policy pdpa: PDPA allowlist not initialized at {path}.",
                file=sys.stderr,
            )
            return 2
        globs = _load_globs(path)
        if ns.glob not in globs:
            print(
                f"sn-setup policy pdpa: glob {ns.glob!r} not in allowlist",
                file=sys.stderr,
            )
            return 2
        globs = [g for g in globs if g != ns.glob]
        _write_globs(path, globs)
        return 0

    if ns.verb == "explain":
        if not path.exists():
            print(
                f"sn-setup policy pdpa: PDPA allowlist not initialized at {path}.",
                file=sys.stderr,
            )
            return 2
        target = ns.path
        for g in _load_globs(path):
            if fnmatch.fnmatch(target, g):
                print(g)
                return 0
        return 1

    return 2
