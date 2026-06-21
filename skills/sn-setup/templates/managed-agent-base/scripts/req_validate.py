#!/usr/bin/env python3
"""Validate REQ frontmatter against docs/requirements/req-schema.json.

Walks `docs/requirements/active/REQ-*.md` and every
`docs/sprints/*/SPRINT-*-*/requirements/REQ-*.md`, parses each file's YAML
frontmatter block, and validates it against the JSON schema shipped at
`docs/requirements/req-schema.json`.

Exit codes:
    0   every REQ validates.
    2   one or more REQs failed validation. Each failure is reported to
        stderr with the offending file + the schema path that failed.
    3   schema file missing or unreadable.

Usage:
    python3 scripts/req_validate.py
    make req-validate

Dependencies: PyYAML and jsonschema. Both are optional — when missing the
script prints an install hint and exits 0 so the workflow does not block
contributors who haven't set up their venv yet.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    print("req_validate: PyYAML not installed — `uv pip install pyyaml jsonschema`. Skipping.",
          file=sys.stderr)
    sys.exit(0)

try:
    from jsonschema import Draft202012Validator  # type: ignore
except ImportError:  # pragma: no cover
    print("req_validate: jsonschema not installed — `uv pip install jsonschema`. Skipping.",
          file=sys.stderr)
    sys.exit(0)


def _find_reqs(root: Path) -> Iterable[Path]:
    for p in (root / "docs" / "requirements" / "active").glob("REQ-*.md"):
        yield p
    for p in (root / "docs" / "sprints").glob("*/SPRINT-*-*/requirements/REQ-*.md"):
        yield p


def _parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    try:
        return yaml.safe_load(block)
    except yaml.YAMLError:
        return None


def main(argv: list[str] | None = None) -> int:
    root = Path.cwd()
    schema_path = root / "docs" / "requirements" / "req-schema.json"
    if not schema_path.exists():
        print(f"req_validate: schema not found at {schema_path}", file=sys.stderr)
        return 3
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    failed = 0
    checked = 0
    for path in sorted(_find_reqs(root)):
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if fm is None:
            print(f"::error file={rel}::no YAML frontmatter found", file=sys.stderr)
            failed += 1
            continue
        errors = sorted(validator.iter_errors(fm), key=lambda e: list(e.path))
        if errors:
            for err in errors:
                loc = ".".join(str(p) for p in err.path) or "<root>"
                print(f"::error file={rel}::{loc}: {err.message}", file=sys.stderr)
            failed += 1
        checked += 1

    if failed:
        print(f"req_validate: {failed}/{checked} REQ file(s) failed validation", file=sys.stderr)
        return 2
    print(f"req_validate: {checked} REQ file(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
