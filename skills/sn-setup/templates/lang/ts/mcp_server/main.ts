// Project-local MCP server using @modelcontextprotocol/sdk.
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

const TOOLS = [
  {
    name: "echo",
    description: "Echo a message back to the caller.",
    inputSchema: {
      type: "object",
      properties: { message: { type: "string" } },
      required: ["message"],
    },
  },
  {
    name: "now",
    description: "Return the current UTC timestamp (ISO-8601).",
    inputSchema: { type: "object", properties: {} },
  },
];

server.setRequestHandler("tools/list", async () => ({ tools: TOOLS }));

server.setRequestHandler("tools/call", async (req: any) => {
  const name = req?.params?.name;
  const args = req?.params?.arguments ?? {};
  if (name === "echo") {
    return { content: [{ type: "text", text: `echo: ${args.message ?? ""}` }] };
  }
  if (name === "now") {
    return { content: [{ type: "text", text: new Date().toISOString() }] };
  }
  return { content: [{ type: "text", text: `unknown tool: ${name}` }], isError: true };
});

const transport = new StdioServerTransport();
await server.connect(transport);
