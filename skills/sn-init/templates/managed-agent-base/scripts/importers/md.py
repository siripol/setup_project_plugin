"""Markdown → RawReq importer."""
from __future__ import annotations

import re
from pathlib import Path

from . import RawReq


def parse(path: Path) -> RawReq:
    text = path.read_text(encoding="utf-8")

    # Title: first H1 line, else filename stem
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem.replace("-", " ").title()

    # Acceptance bullets: lines under a "## Acceptance" heading
    acceptance: list[str] = []
    sect_match = re.search(
        r"(?:^|\n)##\s+(?:Acceptance|Acceptance criteria)\s*\n+(.+?)(?:\n##\s+|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if sect_match:
        for line in sect_match.group(1).splitlines():
            ln = line.strip()
            if ln.startswith(("-", "*")):
                acceptance.append(ln.lstrip("-* ").strip())

    # Priority hint: look for "Priority: high" inline
    priority_match = re.search(r"Priority\s*:\s*(high|medium|low)", text, flags=re.IGNORECASE)
    priority = priority_match.group(1).lower() if priority_match else "medium"

    return RawReq(
        title=title,
        body=text,
        acceptance=acceptance,
        priority=priority,
        source=str(path),
    )
