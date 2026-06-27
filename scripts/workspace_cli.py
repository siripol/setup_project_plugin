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


# B2.2-FU-4: marketplace divergence helpers. Compare a new member service's
# marketplace config against the already-registered members and surface
# stderr warnings. Warn-only; `workspace add` always succeeds regardless.

# Mandatory plugin names per design §6.2 — duplicated here (not imported from
# sn_init) to keep workspace_cli a flat dispatcher without a sn_init dep.
MARKETPLACE_MANDATORY_NAMES: frozenset[str] = frozenset({"core-workflow", "core-guardrails"})


def _collect_marketplace_state(service_path: Path) -> dict:
    """Read marketplace state for a single service path.

    Returns:
        {
          "slug": str,
          "source": str | None,           # marketplace.source from .claude-plugin/marketplace.json
          "plugins": set[str] | None,     # installed_plugins names from .claude/settings.json
          "has_state": bool,              # True iff at least one of the two files was readable
        }
    Missing files / parse errors → null fields, has_state=False (silent skip
    during pairwise compare so legacy / pre-B2.3 members don't generate noise).
    """
    state: dict = {
        "slug": service_path.name,
        "source": None,
        "plugins": None,
        "has_state": False,
    }
    settings_path = service_path / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            plugins_raw = settings.get("installed_plugins")
            if isinstance(plugins_raw, list):
                state["plugins"] = {
                    p["name"] for p in plugins_raw
                    if isinstance(p, dict) and isinstance(p.get("name"), str)
                }
                state["has_state"] = True
        except (json.JSONDecodeError, OSError):
            pass
    manifest_path = service_path / ".claude-plugin" / "marketplace.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            mkt = manifest.get("marketplace")
            if isinstance(mkt, dict):
                source = mkt.get("source")
                if isinstance(source, str) and source.strip():
                    state["source"] = source
                    state["has_state"] = True
        except (json.JSONDecodeError, OSError):
            pass
    return state


def _check_marketplace_divergence(new: dict, existing: list[dict]) -> list[str]:
    """Compare new member state vs each existing member state.

    Returns a list of pre-formatted stderr-ready lines (severity-tagged) to
    print. Empty list → no divergence. The caller decides whether to print
    them; `_cmd_add` does, always to stderr, always non-blocking.

    Severity tags:
        🔴 critical  — marketplace source mismatch, missing mandatory plugin
        🟡 warn      — installed_plugins name-set difference (informational)
    """
    findings: list[str] = []

    # Only compare against members that have actually wired marketplace state.
    # Legacy members predate B2.3 and don't carry the files.
    comparable = [e for e in existing if e["has_state"]]

    # Red: source mismatch. Report one line per existing member with a
    # different source; deduplicate by source value so we don't spam if
    # five members share the same different source.
    if new["source"] is not None:
        mismatches: dict[str, list[str]] = {}
        for e in comparable:
            if e["source"] is not None and e["source"] != new["source"]:
                mismatches.setdefault(e["source"], []).append(e["slug"])
        for other_src, slugs in sorted(mismatches.items()):
            findings.append(
                f"sn-setup workspace: ⚠ critical: marketplace source mismatch — "
                f"new member uses {new['source']!r}; existing member(s) "
                f"{sorted(slugs)!r} use {other_src!r}."
            )

    # Red: missing mandatory. Only fires when at least one existing comparable
    # member ships the mandatory plugin AND the new member doesn't. Silent if
    # everyone is missing it (treats the workspace as collectively pre-B2.3).
    if new["plugins"] is not None:
        for mandatory in sorted(MARKETPLACE_MANDATORY_NAMES):
            if mandatory in new["plugins"]:
                continue
            others_with = [e["slug"] for e in comparable
                           if e["plugins"] is not None and mandatory in e["plugins"]]
            if others_with:
                findings.append(
                    f"sn-setup workspace: ⚠ critical: new member missing mandatory "
                    f"plugin {mandatory!r} (existing member(s) {sorted(others_with)!r} ship it)."
                )

    # Yellow: name-set difference vs the union of comparable members'
    # installed_plugins, with mandatory plugins already covered above
    # excluded so we don't double-count.
    if new["plugins"] is not None and comparable:
        union: set[str] = set()
        for e in comparable:
            if e["plugins"] is not None:
                union |= e["plugins"]
        if union:
            covered_mandatory = MARKETPLACE_MANDATORY_NAMES
            extra_in_new = (new["plugins"] - union) - covered_mandatory
            missing_in_new = (union - new["plugins"]) - covered_mandatory
            diff_bits: list[str] = []
            if extra_in_new:
                diff_bits.append(f"new-only={sorted(extra_in_new)}")
            if missing_in_new:
                diff_bits.append(f"existing-only={sorted(missing_in_new)}")
            if diff_bits:
                findings.append(
                    f"sn-setup workspace: ⚠ warn: installed_plugins set "
                    f"differs from existing members ({', '.join(diff_bits)})."
                )

    return findings


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

    # B2.2-FU-4: marketplace divergence warning. Compare the new member's
    # marketplace state against already-registered members BEFORE appending
    # to the registry (so the warnings reference the pre-add member set).
    # Warn-only — `add` always succeeds regardless of findings.
    new_state = _collect_marketplace_state(service_path)
    existing_states = [
        _collect_marketplace_state(root / s["path"])
        for s in reg["services"]
    ]
    for line in _check_marketplace_divergence(new_state, existing_states):
        print(line, file=sys.stderr)

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
