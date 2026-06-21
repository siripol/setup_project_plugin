// Project-local MCP server stub using @modelcontextprotocol/sdk.
// Registered in mcp/mcp.json. Started by `make mcp-server`.

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  {
    name: "${name}-mcp",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

// Wire up tools here, e.g.:
//   server.setRequestHandler("tools/list", async () => ({ tools: [{ name: "echo", inputSchema: { ... } }] }));
//   server.setRequestHandler("tools/call", async (req) => ({ content: [{ type: "text", text: `echo: ${req.params.arguments.message}` }] }));

const transport = new StdioServerTransport();
await server.connect(transport);
