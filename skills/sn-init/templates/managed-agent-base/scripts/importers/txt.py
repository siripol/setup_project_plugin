"""Plain text → RawReq importer.

Heuristic: first non-empty line = title, subsequent bullet-like lines = acceptance.
"""
from __future__ import annotations

from pathlib import Path

from . import RawReq


def parse(path: Path) -> RawReq:
    lines = [ln.rstrip() for ln in path.read_text(encoding="utf-8").splitlines()]
    title = next((ln for ln in lines if ln.strip()), path.stem.replace("_", " "))

    acceptance: list[str] = []
    for ln in lines[1:]:
        stripped = ln.strip()
        if stripped.startswith(("-", "*", "•")) or (stripped[:2].endswith(".") and stripped[:1].isdigit()):
            acceptance.append(stripped.lstrip("-*•0123456789. ").strip())

    return RawReq(
        title=title.strip(),
        body="\n".join(lines),
        acceptance=acceptance,
        source=str(path),
    )
