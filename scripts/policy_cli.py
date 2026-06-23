"""`sn-setup policy ...` sub-command dispatcher.

Real catalog root resolves to
`<plugin_root>/skills/sn-setup/templates/policies/`; tests override via the
SN_POLICY_CATALOG_ROOT env var.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import policy_apply
import policy_errors
import policy_loader

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_ROOT = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "policies"


def _catalog_root() -> Path:
    override = os.environ.get("SN_POLICY_CATALOG_ROOT")
    return Path(override) if override else DEFAULT_CATALOG_ROOT


def _load_catalog() -> dict[str, policy_loader.PolicyMeta]:
    return policy_loader.load_catalog(_catalog_root())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sn-setup policy", add_help=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")
    sp_show = sub.add_parser("show"); sp_show.add_argument("slug")
    sp_app = sub.add_parser("apply"); sp_app.add_argument("slugs", nargs="+")
    sp_app.add_argument("--with-deps", action="store_true")
    sp_rm = sub.add_parser("remove"); sp_rm.add_argument("slugs", nargs="+")
    sp_rm.add_argument("--force", action="store_true")
    sp_up = sub.add_parser("upgrade")
    g = sp_up.add_mutually_exclusive_group(required=True)
    g.add_argument("slug", nargs="?")
    g.add_argument("--all", dest="all_flag", action="store_true")
    sp_up.add_argument("--force", action="store_true")
    sub.add_parser("status")
    sub.add_parser("show-applied")
    sp_hist = sub.add_parser("history")
    sp_hist.add_argument("--slug", default=None)
    sp_hist.add_argument("--limit", type=int, default=20)
    sub.add_parser("lint")

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0

    try:
        return _dispatch(ns)
    except policy_errors.PolicyError as e:
        print(f"sn-setup policy: {e}", file=sys.stderr)
        return e.exit_code


def _dispatch(ns: argparse.Namespace) -> int:
    project = Path.cwd().resolve()
    catalog = _load_catalog()

    if ns.cmd == "list":
        for slug in sorted(catalog):
            m = catalog[slug]
            group = f" group={m.group}" if m.group else ""
            print(f"{slug:24s} {m.version:8s} {m.category:14s}{group}")
        return 0

    if ns.cmd == "show":
        if ns.slug not in catalog:
            raise policy_errors.UnknownPolicy(f"unknown policy {ns.slug!r}")
        m = catalog[ns.slug]
        print(f"slug:    {m.slug}")
        print(f"version: {m.version}")
        print(f"group:   {m.group}")
        print(f"title:   {m.title}")
        print(f"category: {m.category}")
        print(f"applies_to: {m.applies_to}")
        print(f"requires: {m.requires}")
        print(f"conflicts_with: {m.conflicts_with}")
        print(f"description: {m.description.strip()}")
        return 0

    if ns.cmd == "apply":
        policy_apply.apply_many(
            project, ns.slugs, catalog, with_deps=ns.with_deps,
        )
        return 0

    if ns.cmd == "remove":
        for slug in ns.slugs:
            policy_apply.remove(project, slug, force=ns.force)
        return 0

    if ns.cmd == "upgrade":
        targets = sorted(catalog) if ns.all_flag else [ns.slug]
        for slug in targets:
            if slug not in catalog:
                raise policy_errors.UnknownPolicy(f"unknown policy {slug!r}")
            try:
                policy_apply.upgrade(project, catalog[slug], force=ns.force)
            except policy_errors.PolicyNotApplied:
                if ns.all_flag:
                    continue  # skip un-applied slugs in bulk upgrade
                raise
        return 0

    if ns.cmd == "status":
        rows = policy_apply.status(project, catalog)
        for r in rows:
            glyph = {"current": "✓", "obsolete": "⚠", "drifted": "◆", "unknown": "✗"}[r.state]
            cv = r.catalog_version or "—"
            print(f"  {glyph} {r.slug:24s} applied={r.applied_version:8s} catalog={cv:8s} ({r.state})")
        return 0

    if ns.cmd == "show-applied":
        import json as _json, policy_state as _ps
        state = _ps.read_state(project)
        print(_json.dumps(state["applied_policies"], indent=2))
        return 0

    if ns.cmd == "history":
        import policy_state as _ps
        state = _ps.read_state(project)
        events = state["policy_history"]
        if ns.slug:
            events = [e for e in events if e.get("slug") == ns.slug or e.get("from") == ns.slug or e.get("to") == ns.slug]
        for e in events[-ns.limit :]:
            print(e)
        return 0

    if ns.cmd == "lint":
        failures = policy_loader.lint(_catalog_root())
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        return 0 if not failures else 1

    return 2
