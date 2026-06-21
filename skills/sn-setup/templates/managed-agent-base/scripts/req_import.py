#!/usr/bin/env python3
"""CLI: convert an md/txt/json/docx/pdf source into a REQ-NNN.md scaffold.

Usage:
    python3 scripts/req_import.py <path>

Auto-detects the importer by extension. Writes the new REQ to
`docs/requirements/active/REQ-<next>-<slug>.md`, auto-incrementing NNN across
all REQ files in the project (requirements/active/ + sprints/active/*/requirements/
+ sprints/completed/*/requirements/).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Allow running as `python3 scripts/req_import.py ...`
sys.path.insert(0, str(Path(__file__).resolve().parent))

from importers import (  # type: ignore  # noqa: E402
    RawReq,
    md as _md,
    txt as _txt,
    json as _json,
    docx as _docx,
    pdf as _pdf,
)

IMPORTERS = {
    ".md": _md.parse,
    ".markdown": _md.parse,
    ".txt": _txt.parse,
    ".json": _json.parse,
    ".docx": _docx.parse,
    ".pdf": _pdf.parse,
}


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    text = text.strip("-")
    return text[:50] or "req"


def find_next_req_id(project_root: Path) -> str:
    pattern = re.compile(r"REQ-(\d+)")
    max_id = 0
    for path in project_root.rglob("REQ-*.md"):
        m = pattern.search(path.name)
        if m:
            max_id = max(max_id, int(m.group(1)))
    return f"REQ-{max_id + 1:03d}"


def render_req(req_id: str, raw: RawReq) -> str:
    acceptance_block = "\n".join(f"  - {a}" for a in raw.acceptance) if raw.acceptance else "  - (TBD)"
    notes = raw.notes or "(Imported from source — review for accuracy.)"
    return f"""---
id: {req_id}
title: {raw.title}
priority: {raw.priority}
requires: []
acceptance:
{acceptance_block}
eval_threshold: 70
imported_from: {raw.source}
---

## Context

(Imported from `{raw.source}`. Edit before assigning to a sprint.)

## What

{raw.body[:2000]}{"..." if len(raw.body) > 2000 else ""}

## Out of scope

(Add what this REQ does NOT cover.)

## Notes

{notes}
"""


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: req_import.py <path>", file=sys.stderr)
        return 2

    src = Path(args[0]).resolve()
    if not src.exists():
        print(f"file not found: {src}", file=sys.stderr)
        return 2

    importer = IMPORTERS.get(src.suffix.lower())
    if importer is None:
        print(f"unsupported extension: {src.suffix}", file=sys.stderr)
        return 2

    raw = importer(src)

    project_root = Path.cwd()
    out_dir = project_root / "docs" / "requirements" / "active"
    out_dir.mkdir(parents=True, exist_ok=True)

    req_id = find_next_req_id(project_root)
    slug = slugify(raw.title)
    out_path = out_dir / f"{req_id}-{slug}.md"
    out_path.write_text(render_req(req_id, raw), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
