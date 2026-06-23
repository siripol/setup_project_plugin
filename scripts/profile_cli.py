"""`sn-setup profile ...` CLI sub-tree.

Auto-detects cwd:
  - .claude-plugin/plugin.json present → edits the template YAML.
  - .sn-init-state.json present → edits .claude/profile-defaults.yaml.
  - Neither → exit 15.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

import policy_errors

VALID_PROFILES = ("microservice", "bff", "frontend")


def _detect_target(cwd: Path) -> tuple[str, Path | None]:
    plugin = cwd / ".claude-plugin" / "plugin.json"
    project = cwd / ".sn-init-state.json"
    if plugin.exists() and project.exists():
        return "ambiguous", None
    if plugin.exists():
        return "plugin", cwd
    if project.exists():
        return "project", cwd
    return "invalid", None


def _yaml_path(target_kind: str, root: Path, profile: str) -> Path:
    if target_kind == "plugin":
        return root / "skills" / "sn-setup" / "templates" / "profile" / profile / "default_policies.yaml"
    return root / ".claude" / "profile-defaults.yaml"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _save(path: Path, profile: str, slugs: list[str]) -> None:
    body = f"profile: {profile}\npolicies:\n" + "".join(f"  - {s}\n" for s in slugs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sn-setup profile", add_help=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")
    sp_show = sub.add_parser("show"); sp_show.add_argument("profile")
    sp_add = sub.add_parser("add"); sp_add.add_argument("slug"); sp_add.add_argument("--profile", required=True)
    sp_rm = sub.add_parser("remove"); sp_rm.add_argument("slug"); sp_rm.add_argument("--profile", required=True)
    sp_sw = sub.add_parser("swap"); sp_sw.add_argument("--profile", required=True)
    sp_sw.add_argument("from_slug"); sp_sw.add_argument("to_slug")

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0

    try:
        return _dispatch(ns)
    except policy_errors.PolicyError as e:
        print(f"sn-setup profile: {e}", file=sys.stderr)
        return e.exit_code


def _dispatch(ns: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    kind, root = _detect_target(cwd)
    if kind == "ambiguous":
        raise policy_errors.CwdAmbiguousOrInvalid(
            "cwd has both .claude-plugin/plugin.json and .sn-init-state.json; "
            "pass --target=plugin|project"
        )
    if kind == "invalid":
        raise policy_errors.CwdAmbiguousOrInvalid(
            "sn-setup profile must run inside a plugin repo or a scaffolded project"
        )

    if ns.cmd == "list":
        if kind == "plugin":
            base = root / "skills" / "sn-setup" / "templates" / "profile"
            for child in sorted(p for p in base.iterdir() if p.is_dir()):
                y = child / "default_policies.yaml"
                if y.exists():
                    data = _load(y)
                    print(f"{child.name}: {data.get('policies', [])}")
        else:
            data = _load(root / ".claude" / "profile-defaults.yaml")
            print(f"{data.get('profile', '?')}: {data.get('policies', [])}")
        return 0

    if ns.cmd == "show":
        path = _yaml_path(kind, root, ns.profile)
        if not path.exists():
            raise policy_errors.UnknownProfile(f"profile {ns.profile!r} has no defaults file at {path}")
        print(path.read_text())
        return 0

    profile = ns.profile
    if profile not in VALID_PROFILES:
        raise policy_errors.UnknownProfile(
            f"unknown profile {profile!r}; valid: {VALID_PROFILES}"
        )

    path = _yaml_path(kind, root, profile)
    data = _load(path)
    policies = list(data.get("policies") or [])

    if ns.cmd == "add":
        if ns.slug not in policies:
            policies.append(ns.slug)
        _save(path, profile, policies)
        return 0

    if ns.cmd == "remove":
        policies = [p for p in policies if p != ns.slug]
        _save(path, profile, policies)
        return 0

    if ns.cmd == "swap":
        policies = [ns.to_slug if p == ns.from_slug else p for p in policies]
        if ns.to_slug not in policies:
            policies.append(ns.to_slug)
        _save(path, profile, policies)
        return 0

    return 2
