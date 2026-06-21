"""Project-local MCP server using fastmcp.

Registered in `mcp/mcp.json`. Started by `make mcp-server`. Exposes two
simple tools: `echo` and `list_project_files`.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    print("fastmcp not installed. Run `make install` first.")
    raise SystemExit(1)


mcp = FastMCP("${name}-mcp")


@mcp.tool()
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"echo: {message}"


@mcp.tool()
def list_project_files(pattern: str = "*") -> list[str]:
    """List files in the project root matching the glob pattern."""
    root = Path(os.environ.get("SN_PROJECT_ROOT", ".")).resolve()
    return sorted(str(p.relative_to(root)) for p in root.rglob(pattern) if p.is_file())


if __name__ == "__main__":
    mcp.run()
