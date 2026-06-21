// Project-local MCP server stub.
//
// Wire up github.com/modelcontextprotocol/go-sdk to expose an `echo` tool.
// Started by Makefile target `make mcp-server`.
package main

import (
	"fmt"
	"os"
)

func main() {
	fmt.Fprintln(os.Stderr, "mcp_server stub. Wire up github.com/modelcontextprotocol/go-sdk.")
	// Pseudocode:
	//   server := mcp.NewServer("${name}-mcp", "0.1.0")
	//   server.AddTool(echoTool())
	//   server.ListenStdio()
}
