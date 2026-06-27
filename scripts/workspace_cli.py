"""`sn-setup workspace ...` sub-command dispatcher.

Mirrors `scripts/policy_cli.py` shape. Workspace is a sibling-dir virtual
monorepo aggregator: WORKSPACE.md (human) + .workspace/registry.json
(machine) + 3 bash scripts (status/sync/launch).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import errors  # type: ignore

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "workspace"

WORKSPACE_VERSION = "1.0.0"
REGISTRY_REL = Path(".workspace") / "registry.json"

MARKER_BEGIN = "<!-- registry:begin -->"
MARKER_END = "<!-- registry:end -->"


def _find_workspace_root(start: Path | None = None) -> Path | None:
    """Walk ancestors of `start` (default cwd) looking for .workspace/registry.json.

    Does not traverse symlinks. Stops at filesystem root.
    """
    p = (start or Path.cwd()).resolve()
    while True:
        if (p / REGISTRY_REL).exists():
            return p
        if p.parent == p:
            return None
        p = p.parent


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic write: tempfile + rename in same dir."""
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _cmd_init(ns: argparse.Namespace) -> int:
    target = Path.cwd() / ns.name
    if target.exists() and any(target.iterdir()):
        print(f"sn-setup workspace: target {target} is non-empty",
              file=sys.stderr)
        return errors.EXIT_USAGE
    target.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    ctx = {"workspace_name": ns.name, "created_at": now}

    for src in TEMPLATE_DIR.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATE_DIR)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        body = src.read_bytes()
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            dst.write_bytes(body)
            continue
        for k, v in ctx.items():
            text = text.replace("${" + k + "}", v)
        dst.write_text(text, encoding="utf-8")
        # Preserve exec bit for scripts/*.sh
        if rel.parts and rel.parts[0] == "scripts" and rel.suffix == ".sh":
            try:
                dst.chmod(0o755)
            except OSError:
                pass

    # Force-fix the registry: even after str.replace templating, ensure
    # the JSON has authoritative values. Defensive against template drift
    # (someone editing the template registry.json by hand and breaking it).
    reg_path = target / REGISTRY_REL
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["workspace_version"] = WORKSPACE_VERSION
    reg["name"] = ns.name
    reg["created_at"] = now
    reg["services"] = []
    _atomic_write_json(reg_path, reg)

    print(f"sn-setup workspace: initialized at {target}")
    return errors.EXIT_OK


def _cmd_add(ns: argparse.Namespace) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace (no .workspace/registry.json found)",
              file=sys.stderr)
        return errors.EXIT_USAGE

    service_path = Path(ns.path).resolve()
    if not service_path.is_dir():
        print(f"sn-setup workspace: {service_path} is not a directory",
              file=sys.stderr)
        return errors.EXIT_USAGE
    if not (service_path / ".git").exists():
        print(f"sn-setup workspace: {service_path} is not a git repo",
              file=sys.stderr)
        return errors.EXIT_USAGE

    slug = service_path.name
    reg_path = root / REGISTRY_REL
    reg = json.loads(reg_path.read_text(encoding="utf-8"))

    if any(s["slug"] == slug for s in reg["services"]):
        print(f"sn-setup workspace: slug {slug!r} already registered",
              file=sys.stderr)
        return errors.EXIT_USAGE

    # Auto-collect profile/lang/regulated from member state.
    state_file = service_path / ".sn-init-state.json"
    profile: str | None = None
    lang: str | None = None
    regulated: bool | None = None
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            profile = state.get("profile")
            lang = state.get("lang")
            regulated = state.get("regulated")
        except (json.JSONDecodeError, OSError):
            pass  # null fields on parse failure

    # Owners: --owners flag > null (CODEOWNERS parse is best-effort, out of scope for v1)
    owners: str | None = ns.owners

    # repo_url best-effort.
    repo_url: str | None = None
    try:
        proc = subprocess.run(
            ["git", "-C", str(service_path), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            repo_url = proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    rel = os.path.relpath(service_path, start=root)
    entry = {
        "slug": slug,
        "path": rel,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "lang": lang,
        "regulated": regulated,
        "repo_url": repo_url,
        "owners": owners,
    }
    reg["services"].append(entry)
    reg["services"].sort(key=lambda s: s["slug"])
    _atomic_write_json(reg_path, reg)

    # Append workspace dir name to member's .gitignore (idempotent).
    ws_name = root.name
    gi = service_path / ".gitignore"
    line = f"{ws_name}/"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line not in existing.splitlines():
        new = existing
        if existing and not existing.endswith("\n"):
            new += "\n"
        new += line + "\n"
        gi.write_text(new, encoding="utf-8")

    print(f"sn-setup workspace: registered {slug} from {rel}")
    return errors.EXIT_OK


def _cmd_remove(ns: argparse.Namespace) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace",
              file=sys.stderr)
        return errors.EXIT_USAGE

    reg_path = root / REGISTRY_REL
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    before = len(reg["services"])
    reg["services"] = [s for s in reg["services"] if s["slug"] != ns.slug]
    if len(reg["services"]) == before:
        print(f"sn-setup workspace: {ns.slug!r} not registered",
              file=sys.stderr)
        return errors.EXIT_OK
    _atomic_write_json(reg_path, reg)
    print(f"sn-setup workspace: unregistered {ns.slug}")
    return errors.EXIT_OK


def _cmd_list(_ns: argparse.Namespace) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace",
              file=sys.stderr)
        return errors.EXIT_USAGE

    reg = json.loads((root / REGISTRY_REL).read_text(encoding="utf-8"))
    services = reg["services"]

    # Print human-readable table.
    print(f"{'slug':<24} {'profile':<14} {'lang':<6} {'regulated':<10} path")
    for s in services:
        regulated = "yes" if s.get("regulated") else "no" if s.get("regulated") is False else "?"
        print(f"{s['slug']:<24} {(s.get('profile') or '-'): <14} "
              f"{(s.get('lang') or '-'): <6} {regulated:<10} {s['path']}")

    # Regenerate marker blocks in WORKSPACE.md and CLAUDE.md.
    workspace_md = root / "WORKSPACE.md"
    if workspace_md.exists():
        _regenerate_markers(workspace_md, _workspace_table(services))
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        _regenerate_markers(claude_md, _claude_ecosystem_table(services))
    return errors.EXIT_OK


def _workspace_table(services: list[dict]) -> str:
    """Markdown table for WORKSPACE.md."""
    rows = ["| Service | Profile | Lang | Path | Owners | Regulated |",
            "|---|---|---|---|---|---|"]
    if not services:
        rows.append("| _(none yet)_ | — | — | — | — | — |")
    else:
        for s in services:
            rows.append(
                "| {slug} | {profile} | {lang} | `{path}` | {owners} | {regulated} |".format(
                    slug=s["slug"],
                    profile=s.get("profile") or "—",
                    lang=s.get("lang") or "—",
                    path=s["path"],
                    owners=s.get("owners") or "—",
                    regulated=("yes" if s.get("regulated") else
                               "no" if s.get("regulated") is False else "—"),
                )
            )
    return "\n".join(rows)


def _claude_ecosystem_table(services: list[dict]) -> str:
    """Markdown table for workspace-level CLAUDE.md."""
    rows = ["| Service | Repo | Profile |",
            "|---|---|---|"]
    if not services:
        rows.append("| _(none yet)_ | — | — |")
    else:
        for s in services:
            repo = s.get("repo_url") or s["path"]
            rows.append(
                f"| {s['slug']} | `{repo}` | {s.get('profile') or '—'} |"
            )
    return "\n".join(rows)


def _regenerate_markers(path: Path, new_block: str) -> None:
    body = path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    replacement = f"{MARKER_BEGIN}\n{new_block}\n{MARKER_END}"
    body2, n = pattern.subn(replacement, body, count=1)
    if n == 0:
        # No markers present — append a fresh block.
        body2 = body.rstrip() + f"\n\n{replacement}\n"
    path.write_text(body2, encoding="utf-8")


def _cmd_run_script(verb: str) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace",
              file=sys.stderr)
        return errors.EXIT_USAGE
    script = root / "scripts" / f"{verb}.sh"
    if not script.exists():
        print(f"sn-setup workspace: missing {script}",
              file=sys.stderr)
        return errors.EXIT_INTERNAL
    return subprocess.call(["bash", str(script)], cwd=str(root))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sn-setup workspace")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp_init = sub.add_parser("init"); sp_init.add_argument("name")
    sp_add = sub.add_parser("add"); sp_add.add_argument("path")
    sp_add.add_argument("--owners", default=None,
                        help="Override owners (comma-list of team handles)")
    sp_rm = sub.add_parser("remove"); sp_rm.add_argument("slug")
    sub.add_parser("list")
    sub.add_parser("status")
    sub.add_parser("sync")
    sub.add_parser("launch")

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return errors.EXIT_USAGE if e.code else errors.EXIT_OK

    if ns.cmd == "init":
        return _cmd_init(ns)
    if ns.cmd == "add":
        return _cmd_add(ns)
    if ns.cmd == "remove":
        return _cmd_remove(ns)
    if ns.cmd == "list":
        return _cmd_list(ns)
    if ns.cmd in ("status", "sync", "launch"):
        return _cmd_run_script(ns.cmd)
    return errors.EXIT_USAGE
