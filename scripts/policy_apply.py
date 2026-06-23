"""Apply / remove / upgrade orchestration across the five policy layers.

This module owns the lifecycle of a single policy in a single project.
Exclusive-group, requires, and conflicts_with handling are layered on top
in Task 8 (`apply_many`).
"""
from __future__ import annotations

import json
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import policy_claude_md
import policy_loader
import policy_settings_merge
import policy_state

DOCS_DIR = ".claude/docs/policies"
RULES_DIR = ".claude/rules"
SETTINGS_PATH = ".claude/settings.json"


@dataclass
class ApplyReport:
    slug: str = ""
    applied_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    swap_from: str | None = None
    swap_to: str | None = None
    was_noop: bool = False


def apply(project_dir: Path, meta: policy_loader.PolicyMeta, source: str = "cli") -> ApplyReport:
    state = policy_state.read_state(project_dir)
    report = ApplyReport(slug=meta.slug)

    # Already applied at same version?
    existing = _find_applied(state, meta.slug)
    if existing and existing["version"] == meta.version:
        report.was_noop = True
        return report

    content_sha: dict[str, str] = {}

    # CLAUDE.md row.
    claude_md_path = project_dir / "CLAUDE.md"
    src_text = claude_md_path.read_text(encoding="utf-8") if claude_md_path.exists() else ""
    row = (meta.root / meta.files["claude_md_row"]).read_text(encoding="utf-8").strip("\n")
    new_text, row_sha = policy_claude_md.upsert_row(src_text, meta.slug, row)
    claude_md_path.write_text(new_text, encoding="utf-8")
    content_sha[f"CLAUDE.md#row:{meta.slug}"] = row_sha
    report.applied_files.append("CLAUDE.md#row")

    # Docs.
    docs_dst = project_dir / DOCS_DIR / f"{meta.slug}.md"
    docs_dst.parent.mkdir(parents=True, exist_ok=True)
    docs_src = meta.root / meta.files["docs"]
    if docs_dst.exists():
        report.skipped_files.append(str(docs_dst.relative_to(project_dir)))
    else:
        shutil.copyfile(docs_src, docs_dst)
        content_sha[str(docs_dst.relative_to(project_dir))] = policy_state.sha256_file(docs_dst)
        report.applied_files.append(str(docs_dst.relative_to(project_dir)))

    # Rules (optional).
    if meta.files.get("rules"):
        rules_dst = project_dir / RULES_DIR / f"{meta.slug}.md"
        rules_dst.parent.mkdir(parents=True, exist_ok=True)
        if rules_dst.exists():
            report.skipped_files.append(str(rules_dst.relative_to(project_dir)))
        else:
            shutil.copyfile(meta.root / meta.files["rules"], rules_dst)
            content_sha[str(rules_dst.relative_to(project_dir))] = policy_state.sha256_file(rules_dst)
            report.applied_files.append(str(rules_dst.relative_to(project_dir)))

    # Settings patch (optional).
    settings_marker: str | None = None
    if meta.files.get("settings_patch"):
        patch = json.loads((meta.root / meta.files["settings_patch"]).read_text(encoding="utf-8"))
        settings_path = project_dir / SETTINGS_PATH
        existing_settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        policy_settings_merge.apply_patch(existing_settings, patch, expected_policy=meta.slug)
        settings_path.write_text(json.dumps(existing_settings, indent=2) + "\n", encoding="utf-8")
        settings_marker = meta.slug
        report.applied_files.append(SETTINGS_PATH)

    # Extras (optional).
    for pair in meta.files.get("extras") or []:
        src_rel, dst_rel = pair.split(":", 1)
        dst = project_dir / dst_rel
        if dst.exists():
            report.skipped_files.append(dst_rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(meta.root / src_rel, dst)
        if dst_rel.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content_sha[dst_rel] = policy_state.sha256_file(dst)
        report.applied_files.append(dst_rel)

    # Record in state.
    now = datetime.now(timezone.utc).isoformat()
    state["applied_policies"] = [p for p in state["applied_policies"] if p["slug"] != meta.slug]
    state["applied_policies"].append({
        "slug": meta.slug,
        "version": meta.version,
        "applied_at": now,
        "content_sha": content_sha,
        "settings_marker": settings_marker,
    })
    state["applied_policies"].sort(key=lambda p: p["slug"])
    state["policy_history"].append({
        "action": "apply",
        "slug": meta.slug,
        "version": meta.version,
        "at": now,
        "source": source,
    })
    policy_state.write_state(project_dir, state)
    return report


def _find_applied(state: dict, slug: str) -> dict | None:
    for p in state["applied_policies"]:
        if p["slug"] == slug:
            return p
    return None


@dataclass
class RemoveReport:
    slug: str = ""
    deleted_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


def _semver_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("-")[0].split("."))


def remove(
    project_dir: Path,
    slug: str,
    *,
    force: bool = False,
    source: str = "cli",
    suppress_history: bool = False,
) -> RemoveReport:
    import policy_errors

    state = policy_state.read_state(project_dir)
    entry = _find_applied(state, slug)
    if entry is None:
        raise policy_errors.PolicyNotApplied(
            f"'{slug}' is not applied to this project"
        )

    report = RemoveReport(slug=slug)
    content_sha: dict = entry.get("content_sha") or {}

    for rel, expected_sha in content_sha.items():
        if rel.startswith("CLAUDE.md#row:"):
            # Handled below alongside the actual CLAUDE.md edit.
            continue
        path = project_dir / rel
        if not path.exists():
            continue
        actual_sha = policy_state.sha256_file(path)
        if actual_sha != expected_sha and not force:
            report.skipped_files.append(rel)
            continue
        path.unlink()
        report.deleted_files.append(rel)

    # Strip CLAUDE.md row + settings.json entries.
    claude_md = project_dir / "CLAUDE.md"
    if claude_md.exists():
        claude_md.write_text(
            policy_claude_md.strip_row(claude_md.read_text(encoding="utf-8"), slug),
            encoding="utf-8",
        )
    if entry.get("settings_marker"):
        settings_path = project_dir / SETTINGS_PATH
        if settings_path.exists():
            data = json.loads(settings_path.read_text())
            policy_settings_merge.remove_policy(data, slug)
            settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    state["applied_policies"] = [p for p in state["applied_policies"] if p["slug"] != slug]
    if not suppress_history:
        now = datetime.now(timezone.utc).isoformat()
        state["policy_history"].append({
            "action": "remove",
            "slug": slug,
            "version": entry["version"],
            "at": now,
            "skipped_files": report.skipped_files,
            "source": source,
        })
    policy_state.write_state(project_dir, state)
    return report


@dataclass
class UpgradeReport:
    slug: str = ""
    from_version: str = ""
    to_version: str = ""
    refreshed_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


@dataclass
class StatusEntry:
    slug: str
    applied_version: str
    catalog_version: str | None
    state: str  # "current" | "obsolete" | "unknown" | "drifted"


def upgrade(project_dir: Path, new_meta: policy_loader.PolicyMeta, *, force: bool = False) -> UpgradeReport:
    import policy_errors

    state = policy_state.read_state(project_dir)
    entry = _find_applied(state, new_meta.slug)
    if entry is None:
        raise policy_errors.PolicyNotApplied(f"'{new_meta.slug}' is not applied")
    if entry["version"] == new_meta.version:
        return UpgradeReport(
            slug=new_meta.slug, from_version=entry["version"], to_version=new_meta.version,
        )
    if _semver_tuple(entry["version"]) > _semver_tuple(new_meta.version):
        raise policy_errors.CatalogDowngrade(
            f"state has {new_meta.slug}@{entry['version']} but catalog only "
            f"has {new_meta.version}"
        )

    report = UpgradeReport(
        slug=new_meta.slug,
        from_version=entry["version"],
        to_version=new_meta.version,
    )

    content_sha: dict[str, str] = {}

    # CLAUDE.md row.
    claude_md = project_dir / "CLAUDE.md"
    src = claude_md.read_text(encoding="utf-8")
    row = (new_meta.root / new_meta.files["claude_md_row"]).read_text(encoding="utf-8").strip("\n")
    new_text, row_sha = policy_claude_md.upsert_row(src, new_meta.slug, row)
    claude_md.write_text(new_text, encoding="utf-8")
    content_sha[f"CLAUDE.md#row:{new_meta.slug}"] = row_sha
    report.refreshed_files.append("CLAUDE.md#row")

    # File-by-file refresh.
    file_entries: list[tuple[str, str]] = []  # (rel_path, src_path)
    file_entries.append(
        (f"{DOCS_DIR}/{new_meta.slug}.md", str(new_meta.root / new_meta.files["docs"]))
    )
    if new_meta.files.get("rules"):
        file_entries.append(
            (f"{RULES_DIR}/{new_meta.slug}.md", str(new_meta.root / new_meta.files["rules"]))
        )
    for pair in new_meta.files.get("extras") or []:
        src_rel, dst_rel = pair.split(":", 1)
        file_entries.append((dst_rel, str(new_meta.root / src_rel)))

    for rel, src_path in file_entries:
        dst = project_dir / rel
        recorded = (entry.get("content_sha") or {}).get(rel)
        if dst.exists():
            actual = policy_state.sha256_file(dst)
            if recorded and actual != recorded and not force:
                report.skipped_files.append(rel)
                continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dst)
        if rel.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content_sha[rel] = policy_state.sha256_file(dst)
        report.refreshed_files.append(rel)

    # Settings patch (replace by (matcher, policy); _settings_merge handles version bump).
    settings_marker = entry.get("settings_marker")
    if new_meta.files.get("settings_patch"):
        patch = json.loads((new_meta.root / new_meta.files["settings_patch"]).read_text())
        settings_path = project_dir / SETTINGS_PATH
        data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        policy_settings_merge.apply_patch(data, patch, expected_policy=new_meta.slug)
        settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        settings_marker = new_meta.slug

    now = datetime.now(timezone.utc).isoformat()
    state["applied_policies"] = [p for p in state["applied_policies"] if p["slug"] != new_meta.slug]
    state["applied_policies"].append({
        "slug": new_meta.slug,
        "version": new_meta.version,
        "applied_at": now,
        "content_sha": content_sha,
        "settings_marker": settings_marker,
    })
    state["applied_policies"].sort(key=lambda p: p["slug"])
    state["policy_history"].append({
        "action": "upgrade",
        "slug": new_meta.slug,
        "from": entry["version"],
        "to": new_meta.version,
        "at": now,
        "skipped_files": report.skipped_files,
        "source": "cli",
    })
    policy_state.write_state(project_dir, state)
    return report


def apply_many(
    project_dir: Path,
    slugs: list[str],
    catalog: dict[str, policy_loader.PolicyMeta],
    *,
    with_deps: bool = False,
    source: str = "cli",
) -> list[ApplyReport]:
    import policy_errors

    # 1. Validate every slug exists in catalog.
    for s in slugs:
        if s not in catalog:
            raise policy_errors.UnknownPolicy(
                f"unknown policy {s!r}; see `sn-setup policy list`"
            )

    # 2. Expand requires (BFS) when --with-deps; else verify they are already
    #    in applied_policies.
    state = policy_state.read_state(project_dir)
    applied_slugs = {p["slug"] for p in state["applied_policies"]}

    ordered: list[str] = []
    seen: set[str] = set()

    def visit(slug: str) -> None:
        if slug in seen:
            return
        meta = catalog[slug]
        for req in meta.requires:
            if req in applied_slugs:
                continue
            if not with_deps:
                if req not in slugs:
                    raise policy_errors.RequiresNotSatisfied(
                        f"'{slug}' requires {req!r} which is not applied; "
                        "pass --with-deps to auto-install"
                    )
            else:
                if req in catalog:
                    visit(req)
                else:
                    raise policy_errors.UnknownPolicy(
                        f"required dep {req!r} of {slug!r} not in catalog"
                    )
        if slug not in seen:
            ordered.append(slug)
            seen.add(slug)

    for s in slugs:
        visit(s)

    # 3. Plan exclusive-group swaps.
    swap_plan: list[tuple[str, str]] = []  # (incumbent, replacement)
    for s in ordered:
        meta = catalog[s]
        if meta.group is None:
            continue
        for p in list(state["applied_policies"]):
            if p["slug"] == s:
                continue
            other_meta = catalog.get(p["slug"])
            if other_meta and other_meta.group == meta.group:
                swap_plan.append((p["slug"], s))

    # 4. conflicts_with check.
    for s in ordered:
        meta = catalog[s]
        for c in meta.conflicts_with:
            if c in applied_slugs and not any(c == inc for inc, _ in swap_plan):
                raise policy_errors.ConflictsWithViolation(
                    f"'{s}' conflicts with already-applied '{c}'"
                )

    # 5. Execute swaps (remove incumbent) — non-force; user-edited files preserved.
    for incumbent, replacement in swap_plan:
        remove(project_dir, incumbent, source=source, suppress_history=True)
        # Record one explicit swap event in place of the suppressed remove.
        state = policy_state.read_state(project_dir)
        now = datetime.now(timezone.utc).isoformat()
        state["policy_history"].append({
            "action": "swap",
            "from": incumbent,
            "to": replacement,
            "at": now,
            "source": source,
        })
        policy_state.write_state(project_dir, state)

    # 6. Apply in dependency order.
    reports: list[ApplyReport] = []
    for s in ordered:
        reports.append(apply(project_dir, catalog[s], source=source))
    return reports


def status(project_dir: Path, catalog: dict[str, policy_loader.PolicyMeta]) -> list[StatusEntry]:
    state = policy_state.read_state(project_dir)
    out: list[StatusEntry] = []
    for p in state["applied_policies"]:
        slug = p["slug"]
        meta = catalog.get(slug)
        if meta is None:
            out.append(StatusEntry(slug, p["version"], None, "unknown"))
            continue
        # drift detection
        drift = False
        for rel, sha in (p.get("content_sha") or {}).items():
            if rel.startswith("CLAUDE.md#row:"):
                continue
            path = project_dir / rel
            if path.exists() and policy_state.sha256_file(path) != sha:
                drift = True
                break
        cv = meta.version
        if p["version"] == cv:
            out.append(StatusEntry(slug, p["version"], cv, "drifted" if drift else "current"))
        elif _semver_tuple(p["version"]) < _semver_tuple(cv):
            out.append(StatusEntry(slug, p["version"], cv, "obsolete"))
        else:
            out.append(StatusEntry(slug, p["version"], cv, "unknown"))
    return out
