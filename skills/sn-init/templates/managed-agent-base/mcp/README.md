# mcp/

Model Context Protocol (MCP) server configuration.

- `mcp.json` — registry of MCP servers to attach to the agent. The default entry points at the project-local stub in `mcp_server/`.

Add external MCP servers (Playwright, GitHub, etc.) as additional entries in `servers[]`.
