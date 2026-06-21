// Tier 2 — local agent loop via anthropic-sdk-go BetaToolRunner.
//
// This is a runnable stub. Replace the example tool with your real tools.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
)

func main() {
	ctx := context.Background()
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		log.Fatal("set ANTHROPIC_API_KEY in env")
	}

	// Pseudocode — actual API requires anthropic-sdk-go (run `make install` first).
	//
	//   client := anthropic.NewClient()
	//   runner := toolrunner.NewBetaToolRunner(client, []toolrunner.Tool{exampleTool()})
	//   out, err := runner.Run(ctx, "${model}", "Say hello and call the example tool.")
	//   if err != nil { log.Fatal(err) }
	//   fmt.Println(out.Text)
	_ = ctx
	demo, _ := json.MarshalIndent(map[string]any{
		"model":   "${model}",
		"thinking": map[string]string{"type": "adaptive"},
		"tool":    exampleToolDefinition(),
	}, "", "  ")
	fmt.Printf("agent.go stub. Wire up BetaToolRunner. Defaults:\n%s\n", demo)
}

// exampleToolDefinition returns a JSON-Schema tool definition for a single
// "echo" tool. Replace with your real tools.
func exampleToolDefinition() map[string]any {
	return map[string]any{
		"name":        "echo",
		"description": "Echo a message back to the user.",
		"input_schema": map[string]any{
			"type": "object",
			"properties": map[string]any{
				"message": map[string]any{"type": "string"},
			},
			"required": []string{"message"},
		},
	}
}
