"""JSON → RawReq importer.

Expected shape (any subset accepted):
{
  "title": "...",
  "body": "...",          // optional, free-form description
  "acceptance": ["...", "..."],
  "priority": "high",     // optional: high|medium|low
  "notes": "..."          // optional
}
"""
from __future__ import annotations

import json as _json
from pathlib import Path

from . import RawReq


def parse(path: Path) -> RawReq:
    data = _json.loads(path.read_text(encoding="utf-8"))
    return RawReq(
        title=str(data.get("title", path.stem)),
        body=str(data.get("body", "")),
        acceptance=[str(a) for a in data.get("acceptance", [])],
        priority=str(data.get("priority", "medium")).lower(),
        notes=str(data.get("notes", "")),
        source=str(path),
    )
