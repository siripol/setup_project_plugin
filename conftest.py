"""Top-level pytest config.

Excludes the scaffolder's template tree from collection. Pytest would
otherwise discover the placeholder smoke tests under
`skills/sn-setup/templates/lang/py/tests/`, compile them, and leave .pyc
cache that the scaffolder's render walker then tries to read as UTF-8 —
producing UnicodeDecodeError on the *next* legitimate scaffold run.

Tests live in `tests/`. Template content is for scaffolded projects to
inherit, not for our suite to execute.
"""
from __future__ import annotations

collect_ignore_glob = ["skills/sn-setup/templates/*"]
