// Project-local MCP server.
//
// Uses `github.com/modelcontextprotocol/go-sdk` to expose `echo` and `now`
// tools over stdio. Registered in `mcp/mcp.json`; start with `make mcp-server`.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	mcp "github.com/modelcontextprotocol/go-sdk/mcp"
)

type echoArgs struct {
	Message string `json:"message"`
}

func main() {
	server := mcp.NewServer(mcp.ServerInfo{Name: "${name}-mcp", Version: "0.1.0"})

	server.RegisterTool(mcp.Tool{
		Name:        "echo",
		Description: "Echo a message back to the caller.",
		InputSchema: json.RawMessage(`{"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}`),
		Handler: func(ctx context.Context, raw json.RawMessage) (any, error) {
			var args echoArgs
			if err := json.Unmarshal(raw, &args); err != nil {
				return nil, err
			}
			return fmt.Sprintf("echo: %s", args.Message), nil
		},
	})

	server.RegisterTool(mcp.Tool{
		Name:        "now",
		Description: "Return the current UTC timestamp (RFC3339).",
		InputSchema: json.RawMessage(`{"type":"object","properties":{}}`),
		Handler: func(_ context.Context, _ json.RawMessage) (any, error) {
			return time.Now().UTC().Format(time.RFC3339), nil
		},
	})

	if err := server.ServeStdio(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
