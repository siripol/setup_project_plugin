"""ObsidianClient — read/write the Obsidian knowledge vault.

Backends, in priority order:
  1. MCP — if any of `mcp__obsidian__*`, `mcp__mcp-obsidian__*`,
     `mcp__obsidian-mcp__*` tool prefixes are reachable, route writes
     through MCP so backlinks update and Dataview cache invalidates.
  2. Filesystem — plain `Write` via the local vault path. Offline-friendly
     fallback.

The probe is best-effort: when invoked outside a Claude Code session (where
MCP tools aren't reachable from a plain Python script), `probe_mcp()` always
returns `False` and the client uses the filesystem backend.

Selection is also gated by the `--obsidian-mcp` flag persisted in
`.sn-init-state.json`. `on` requires MCP (raises on miss), `off` forces
filesystem, `auto` (default) does the probe.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


# Known MCP tool prefixes for Obsidian servers (community + official).
MCP_PROBES = [
    "mcp__obsidian__",
    "mcp__mcp-obsidian__",
    "mcp__obsidian-mcp__",
]


@dataclass
class ObsidianConfig:
    vault_root: Path
    mode: str = "auto"  # "auto" | "on" | "off"
    project: str = ""
    knowledge_scope: str = "project"  # "project" | "global"


class ObsidianBackendMissing(Exception):
    """Raised when --obsidian-mcp=on but no Obsidian MCP server is reachable."""


def probe_mcp() -> str | None:
    """Return the first reachable MCP server prefix, or None.

    Probe strategy: a `claude` CLI invocation can list available MCP tools
    via `claude mcp list-tools` (when run inside a Claude Code session).
    Outside the session, we cannot reach MCP — return None.
    """
    # Cheap env-var hint: orchestrator sets SN_OBSIDIAN_MCP_PREFIX after a
    # successful tool-search lookup. If unset, fall back to the file probe.
    hinted = os.environ.get("SN_OBSIDIAN_MCP_PREFIX")
    if hinted in MCP_PROBES:
        return hinted

    # Outside Claude Code: nothing to probe.
    return None


def make_client(config: ObsidianConfig) -> "ObsidianClient":
    if config.mode == "off":
        backend = "fs"
    elif config.mode == "on":
        prefix = probe_mcp()
        if not prefix:
            raise ObsidianBackendMissing(
                "Obsidian MCP required (--obsidian-mcp=on) but no MCP server reachable. "
                "Install mcp-obsidian or use --obsidian-mcp=auto."
            )
        backend = "mcp"
    else:  # auto
        backend = "mcp" if probe_mcp() else "fs"
    return ObsidianClient(config=config, backend=backend)


@dataclass
class ObsidianClient:
    config: ObsidianConfig
    backend: str = "fs"

    # --- path helpers ---

    def _bucket_root(self, bucket: str) -> Path:
        """bucket ∈ {project, shared, tech}"""
        root = self.config.vault_root / "knowledge"
        if bucket == "project":
            scope = self.config.project if self.config.knowledge_scope == "project" else "shared"
            return root / "projects" / scope
        if bucket == "shared":
            return root / "global" / "shared"
        if bucket == "tech":
            return root / "global" / "tech" / (self.config.project or "shared")
        raise ValueError(f"unknown bucket: {bucket}")

    # --- writes ---

    def write_topic(self, bucket: str, topic: str, body: str, traceback: dict | None = None) -> Path:
        path = self._bucket_root(bucket) / f"{topic}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        front = _frontmatter(topic, bucket, traceback or {})
        path.write_text(front + body, encoding="utf-8")
        # MCP backend will additionally trigger backlink + Dataview refresh
        # via the orchestrator after this call returns.
        return path

    def read_topic(self, bucket: str, topic: str) -> str | None:
        path = self._bucket_root(bucket) / f"{topic}.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def list_topics(self, bucket: str) -> Iterable[str]:
        root = self._bucket_root(bucket)
        if not root.exists():
            return []
        return [p.stem for p in root.glob("*.md")]

    # --- introspection ---

    def describe(self) -> dict:
        return {
            "backend": self.backend,
            "vault_root": str(self.config.vault_root),
            "project": self.config.project,
            "knowledge_scope": self.config.knowledge_scope,
        }


def _frontmatter(topic: str, bucket: str, traceback: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "topic": topic,
        "bucket": bucket,
        "last_updated": now,
        **traceback,
    }
    lines = ["---"]
    for key, value in payload.items():
        if isinstance(value, list):
            lines.append(f"{key}: {json.dumps(value)}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + "\n"
