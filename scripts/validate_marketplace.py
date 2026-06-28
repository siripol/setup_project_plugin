#!/usr/bin/env python3
"""validate_marketplace — assert platform-marketplace/ catalog + per-plugin manifests are well-formed.

Exit codes:
  0 — valid
  1 — schema violation (catalog or per-plugin)
  2 — self-containment violation (path escape, cross-plugin symlink)
  3 — dependency graph violation (cycle, missing dep, unsatisfiable constraint)
  4 — catalog ↔ per-plugin version desync

Usage:
  python3 scripts/validate_marketplace.py [--marketplace-dir PATH]

Per REQ-MKT-002 Phase 1 (B3.1).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_DIR_DEFAULT = REPO_ROOT / "platform-marketplace"

TEXT_EXTENSIONS = frozenset({
    ".json", ".md", ".sh", ".py", ".ts", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".txt",
})

# Code semantics: exit-code constants.
EXIT_OK = 0
EXIT_SCHEMA = 1
EXIT_SELF_CONTAINMENT = 2
EXIT_DEP_GRAPH = 3
EXIT_VERSION_SYNC = 4


@dataclass(frozen=True)
class ValidationError:
    code: int
    path: Path
    message: str


@dataclass
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)

    def add(self, code: int, path: Path, message: str) -> None:
        self.errors.append(ValidationError(code=code, path=path, message=message))

    def has_errors(self) -> bool:
        return bool(self.errors)

    def exit_code(self) -> int:
        if not self.errors:
            return EXIT_OK
        # Worst-of: highest exit code wins for clarity.
        return max(e.code for e in self.errors)


def _load_json(path: Path, result: ValidationResult) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        result.add(EXIT_SCHEMA, path, f"file not found: {path}")
        return None
    except json.JSONDecodeError as exc:
        result.add(EXIT_SCHEMA, path, f"invalid JSON: {exc.msg} at line {exc.lineno} col {exc.colno}")
        return None


def _load_schema(marketplace_dir: Path, name: str, result: ValidationResult) -> dict | None:
    schema_path = marketplace_dir / ".claude-plugin" / name
    return _load_json(schema_path, result)


def validate_catalog(marketplace_dir: Path, result: ValidationResult) -> dict | None:
    catalog_path = marketplace_dir / ".claude-plugin" / "marketplace.json"
    catalog = _load_json(catalog_path, result)
    if catalog is None:
        return None
    schema = _load_schema(marketplace_dir, "marketplace.schema.json", result)
    if schema is None:
        return None
    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(catalog), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        result.add(EXIT_SCHEMA, catalog_path, f"catalog schema violation at {loc}: {err.message}")
    return catalog


def validate_plugin_manifest(plugin_dir: Path, marketplace_dir: Path, result: ValidationResult) -> dict | None:
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    manifest = _load_json(manifest_path, result)
    if manifest is None:
        return None
    schema = _load_schema(marketplace_dir, "plugin.schema.json", result)
    if schema is None:
        return None
    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        result.add(EXIT_SCHEMA, manifest_path, f"plugin manifest schema violation at {loc}: {err.message}")
    return manifest


_RELATIVE_ESCAPE_RE = re.compile(r"(?:^|[\s\"'=:,(\[])(\.\./[^\s\"'\)\]]*)")


def validate_self_containment(plugin_dir: Path, result: ValidationResult) -> None:
    """Per ADR-MKT-003: no file inside plugin_dir may reference a path outside it
    via relative `../` escape or symlink crossing.
    """
    plugin_dir_resolved = plugin_dir.resolve()
    for path in plugin_dir.rglob("*"):
        if path.is_symlink():
            try:
                target = path.resolve(strict=False)
            except OSError as exc:
                result.add(EXIT_SELF_CONTAINMENT, path, f"symlink unresolvable: {exc}")
                continue
            try:
                target.relative_to(plugin_dir_resolved)
            except ValueError:
                result.add(
                    EXIT_SELF_CONTAINMENT, path,
                    f"symlink escapes plugin boundary: target={target}",
                )
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError as exc:
            result.add(EXIT_SELF_CONTAINMENT, path, f"unreadable: {exc}")
            continue
        for match in _RELATIVE_ESCAPE_RE.finditer(text):
            rel = match.group(1)
            resolved = (path.parent / rel).resolve()
            try:
                resolved.relative_to(plugin_dir_resolved)
            except ValueError:
                result.add(
                    EXIT_SELF_CONTAINMENT, path,
                    f"relative path escapes plugin boundary: '{rel}' resolves to {resolved}",
                )


_CONSTRAINT_RE = re.compile(r"^(?P<op>[~^])?(?P<version>\d+(?:\.\d+){0,2})$")


def _parse_version(v: str) -> tuple[int, int, int]:
    parts = v.split(".")
    while len(parts) < 3:
        parts.append("0")
    return tuple(int(p) for p in parts[:3])  # type: ignore[return-value]


def _constraint_satisfied(constraint: str, version: str) -> bool:
    m = _CONSTRAINT_RE.match(constraint)
    if not m:
        return False
    op = m.group("op")
    target = _parse_version(m.group("version"))
    actual = _parse_version(version)
    if op is None:
        return actual == target
    if op == "^":
        return actual >= target and actual[0] == target[0]
    if op == "~":
        return actual >= target and actual[0] == target[0] and actual[1] == target[1]
    return False


def validate_dependency_graph(catalog: dict, result: ValidationResult, catalog_path: Path) -> None:
    plugins = catalog.get("plugins", [])
    by_name = {p["name"]: p for p in plugins}
    # Edges: name -> [dep_name]
    edges: dict[str, list[str]] = {p["name"]: [] for p in plugins}
    for entry in plugins:
        for dep in entry.get("depends_on", []) or []:
            dep_name = dep["name"]
            constraint = dep["version_constraint"]
            if dep_name not in by_name:
                result.add(
                    EXIT_DEP_GRAPH, catalog_path,
                    f"plugin '{entry['name']}' depends on '{dep_name}' which is not in the catalog",
                )
                continue
            if not _constraint_satisfied(constraint, by_name[dep_name]["version"]):
                result.add(
                    EXIT_DEP_GRAPH, catalog_path,
                    f"plugin '{entry['name']}' depends_on '{dep_name}' with "
                    f"constraint '{constraint}' but catalog version is "
                    f"'{by_name[dep_name]['version']}'",
                )
            edges[entry["name"]].append(dep_name)

    # Cycle detection: DFS with WHITE/GRAY/BLACK coloring.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in edges}

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        for nxt in edges.get(node, []):
            if color.get(nxt, WHITE) == GRAY:
                cycle = stack[stack.index(nxt):] + [nxt] if nxt in stack else [node, nxt]
                result.add(
                    EXIT_DEP_GRAPH, catalog_path,
                    f"dependency cycle detected: {' -> '.join(cycle)}",
                )
                return
            if color.get(nxt, WHITE) == WHITE:
                dfs(nxt, stack + [nxt])
        color[node] = BLACK

    for name in edges:
        if color[name] == WHITE:
            dfs(name, [name])


def validate_version_sync(catalog: dict, marketplace_dir: Path, result: ValidationResult, catalog_path: Path) -> None:
    for entry in catalog.get("plugins", []):
        source = entry.get("source", "")
        if not source.startswith("./"):
            continue
        plugin_dir = marketplace_dir / source[2:].rstrip("/")
        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            result.add(
                EXIT_VERSION_SYNC, catalog_path,
                f"plugin '{entry['name']}' source='{source}' has no plugin.json at {manifest_path}",
            )
            continue
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            result.add(
                EXIT_VERSION_SYNC, manifest_path,
                f"unreadable manifest for '{entry['name']}': {exc}",
            )
            continue
        manifest_version = manifest.get("version")
        if manifest_version != entry["version"]:
            result.add(
                EXIT_VERSION_SYNC, manifest_path,
                f"version desync for '{entry['name']}': "
                f"catalog={entry['version']} manifest={manifest_version}",
            )


def validate_all(marketplace_dir: Path = MARKETPLACE_DIR_DEFAULT) -> int:
    result = ValidationResult()
    catalog_path = marketplace_dir / ".claude-plugin" / "marketplace.json"
    catalog = validate_catalog(marketplace_dir, result)

    if catalog is not None:
        for entry in catalog.get("plugins", []):
            source = entry.get("source", "")
            if not source.startswith("./"):
                continue
            plugin_dir = marketplace_dir / source[2:].rstrip("/")
            if plugin_dir.is_dir():
                validate_plugin_manifest(plugin_dir, marketplace_dir, result)
                validate_self_containment(plugin_dir, result)
        validate_dependency_graph(catalog, result, catalog_path)
        validate_version_sync(catalog, marketplace_dir, result, catalog_path)

    _emit(result.errors)
    return result.exit_code()


def _emit(errors: Iterable[ValidationError]) -> None:
    errors = list(errors)
    if not errors:
        print("validate_marketplace: OK")
        return
    for err in errors:
        print(f"validate_marketplace: [{err.code}] {err.path}: {err.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--marketplace-dir", type=Path, default=MARKETPLACE_DIR_DEFAULT,
        help=f"Path to platform-marketplace dir (default: {MARKETPLACE_DIR_DEFAULT})",
    )
    args = parser.parse_args(argv)
    return validate_all(args.marketplace_dir)


if __name__ == "__main__":
    sys.exit(main())
