// Tier 2 — local agent loop via anthropic-sdk-go.
//
// Sends a single user message via Messages.New and prints the response.
// The Go SDK also ships a `toolrunner` package (BetaToolRunner) for
// auto-driving tool-call loops — see the Anthropic Go SDK docs.
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/anthropics/anthropic-sdk-go"
)

const defaultPrompt = "Summarize this project's structure: read AGENTS.md and the top-level files; report owners, key invariants, and any obvious risks."

func main() {
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		log.Fatal("set ANTHROPIC_API_KEY in env")
	}

	prompt := defaultPrompt
	if len(os.Args) > 1 {
		prompt = strings.Join(os.Args[1:], " ")
	}

	ctx := context.Background()
	client := anthropic.NewClient()

	resp, err := client.Messages.New(ctx, anthropic.MessageNewParams{
		Model:     anthropic.F(anthropic.ModelClaudeOpus4),
		MaxTokens: anthropic.F(int64(1024)),
		Messages: anthropic.F([]anthropic.MessageParam{
			anthropic.NewUserMessage(anthropic.NewTextBlock(prompt)),
		}),
	})
	if err != nil {
		log.Fatal(err)
	}

	for _, block := range resp.Content {
		if block.Type == "text" {
			fmt.Println(block.Text)
		}
	}
}

// exampleToolDefinition shows how to declare a tool for BetaToolRunner.
// Pass a slice of these to `toolrunner.NewBetaToolRunner` when you want
// the SDK to drive tool calls automatically.
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
