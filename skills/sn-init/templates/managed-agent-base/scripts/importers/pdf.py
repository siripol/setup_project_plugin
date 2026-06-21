"""PDF → RawReq importer (requires pypdf)."""
from __future__ import annotations

import re
from pathlib import Path

from . import RawReq


def parse(path: Path) -> RawReq:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "pypdf not installed. `pip install pypdf` to use the pdf importer."
        ) from e

    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    # Title: first non-empty line
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0] if lines else path.stem

    # Acceptance: lines under any heading containing "acceptance"
    acceptance: list[str] = []
    sect = re.search(r"acceptance[^\n]*\n(.+?)(\n[A-Z][a-zA-Z ]{1,30}\n|\Z)", text, flags=re.IGNORECASE | re.DOTALL)
    if sect:
        for ln in sect.group(1).splitlines():
            s = ln.strip()
            if s.startswith(("-", "*", "•")) or (s[:2].endswith(".") and s[:1].isdigit()):
                acceptance.append(s.lstrip("-*•0123456789. ").strip())

    return RawReq(title=title, body=text, acceptance=acceptance, source=str(path))
