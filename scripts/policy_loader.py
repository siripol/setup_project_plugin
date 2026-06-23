"""Catalog loader + lint for scripts/policy_*.py.

Reads policy.yaml from a per-policy directory, validates schema, returns a
typed PolicyMeta dataclass. lint() walks an entire catalog directory and
returns human-readable failure strings (empty list on success).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

import policy_errors

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[\w.]+)?$")
VALID_CATEGORIES = {"security", "conventions", "workflow", "observability"}
REQUIRED_FIELDS = (
    "slug", "title", "version", "category", "group", "applies_to",
    "requires", "conflicts_with", "description", "files",
)


@dataclass
class PolicyMeta:
    slug: str
    title: str
    version: str
    category: str
    group: str | None
    applies_to: list[str]
    requires: list[str]
    conflicts_with: list[str]
    description: str
    files: dict[str, object]
    root: Path = field(default_factory=Path)


def load_policy(dir_path: Path) -> PolicyMeta:
    yaml_path = dir_path / "policy.yaml"
    if not yaml_path.exists():
        raise policy_errors.MalformedPolicy(f"{dir_path}: missing policy.yaml")
    try:
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise policy_errors.MalformedPolicy(f"{yaml_path}: YAML parse error: {e}") from e

    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: missing required fields: {missing}"
        )

    if not SEMVER.match(str(raw["version"])):
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: version {raw['version']!r} is not semver"
        )

    if raw["category"] not in VALID_CATEGORIES:
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: category {raw['category']!r} not in {sorted(VALID_CATEGORIES)}"
        )

    files = raw["files"] or {}
    # Required entries inside `files`.
    for key in ("claude_md_row", "docs"):
        if key not in files:
            raise policy_errors.MalformedPolicy(
                f"{yaml_path}: files.{key} is required"
            )

    # Existence check for every referenced path.
    referenced = []
    for key, val in files.items():
        if key == "extras":
            for pair in val or []:
                src = pair.split(":", 1)[0]
                referenced.append(src)
        elif val:
            referenced.append(val)
    missing_paths = [p for p in referenced if not (dir_path / p).exists()]
    if missing_paths:
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: referenced files missing: {missing_paths}"
        )

    return PolicyMeta(
        slug=str(raw["slug"]),
        title=str(raw["title"]),
        version=str(raw["version"]),
        category=str(raw["category"]),
        group=raw["group"] if raw["group"] is None else str(raw["group"]),
        applies_to=list(raw["applies_to"] or []),
        requires=list(raw["requires"] or []),
        conflicts_with=list(raw["conflicts_with"] or []),
        description=str(raw["description"]),
        files=dict(files),
        root=dir_path,
    )


def load_catalog(catalog_root: Path) -> dict[str, PolicyMeta]:
    out: dict[str, PolicyMeta] = {}
    for child in sorted(catalog_root.iterdir()):
        if not child.is_dir():
            continue
        meta = load_policy(child)
        if meta.slug in out:
            raise policy_errors.MalformedPolicy(
                f"duplicate slug {meta.slug!r} ({out[meta.slug].root} vs {child})"
            )
        out[meta.slug] = meta
    return out


def lint(catalog_root: Path) -> list[str]:
    failures: list[str] = []
    try:
        catalog = load_catalog(catalog_root)
    except policy_errors.MalformedPolicy as e:
        return [str(e)]

    # Circular requires detection.
    def visit(slug: str, stack: list[str]) -> None:
        if slug in stack:
            failures.append(f"circular requires: {' -> '.join(stack + [slug])}")
            return
        meta = catalog.get(slug)
        if meta is None:
            return
        for req in meta.requires:
            visit(req, stack + [slug])

    for slug in catalog:
        visit(slug, [])

    # conflicts_with referencing non-existent slug.
    for slug, meta in catalog.items():
        for c in meta.conflicts_with:
            if c not in catalog:
                failures.append(f"{slug}: conflicts_with unknown slug {c!r}")

    # Orphan requires (a slug declares a `requires: [foo]` where `foo` is not in catalog).
    for slug, meta in catalog.items():
        for req in meta.requires:
            if req not in catalog:
                failures.append(f"{slug}: requires unknown slug {req!r}")

    # Cross-patch settings-marker collisions: every settings.patch.json entry
    # in any array MUST carry `policy: <this slug>`. Author mistakes where one
    # policy's patch entry is tagged with another policy's slug would silently
    # break the remove path.
    import json as _json
    for slug, meta in catalog.items():
        patch_rel = meta.files.get("settings_patch")
        if not patch_rel:
            continue
        try:
            patch = _json.loads((meta.root / patch_rel).read_text(encoding="utf-8"))
        except Exception as e:
            failures.append(f"{slug}: settings.patch.json unreadable: {e}")
            continue
        _walk_for_marker_collisions(patch, slug, failures)

    return failures


def _walk_for_marker_collisions(node: object, expected_slug: str, failures: list[str]) -> None:
    if isinstance(node, dict):
        for v in node.values():
            _walk_for_marker_collisions(v, expected_slug, failures)
    elif isinstance(node, list):
        for entry in node:
            if isinstance(entry, dict) and "policy" in entry:
                if entry["policy"] != expected_slug:
                    failures.append(
                        f"{expected_slug}: settings patch entry tagged "
                        f"policy={entry['policy']!r}, expected {expected_slug!r}"
                    )
            _walk_for_marker_collisions(entry, expected_slug, failures)
