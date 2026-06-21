"""Project-local MCP server stub using fastmcp.

Registered in `mcp/mcp.json`. Started by `make mcp-server`.
"""
from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("fastmcp not installed. Run `make install` first.")
    raise SystemExit(1)


mcp = FastMCP("${name}-mcp")


@mcp.tool()
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"echo: {message}"


if __name__ == "__main__":
    mcp.run()
