// Tier 3 — Managed Agents session driver.
//
// Opens a session against a Managed Agent and streams events until the
// session goes idle. Reads AGENT_ID from env; SN_RUN_CLIENT=1 makes this
// file's init() drive the session at startup.
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/anthropics/anthropic-sdk-go"
)

func RunSession(agentID string) error {
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		return fmt.Errorf("set ANTHROPIC_API_KEY in env")
	}
	if agentID == "" {
		agentID = os.Getenv("AGENT_ID")
	}
	if agentID == "" {
		return fmt.Errorf("set AGENT_ID env var or pass an id to RunSession")
	}

	ctx := context.Background()
	client := anthropic.NewClient()

	session, err := client.Beta.Sessions.New(ctx, anthropic.BetaSessionNewParams{
		AgentID: anthropic.F(agentID),
	})
	if err != nil {
		return fmt.Errorf("create session: %w", err)
	}
	fmt.Printf("session: %s\n", session.ID)

	stream := client.Beta.Sessions.Events.Stream(ctx, session.ID)
	for stream.Next() {
		fmt.Println(stream.Current())
	}
	if err := stream.Err(); err != nil {
		return fmt.Errorf("stream: %w", err)
	}
	return nil
}

func init() {
	if os.Getenv("SN_RUN_CLIENT") != "1" {
		return
	}
	if err := RunSession(os.Getenv("AGENT_ID")); err != nil {
		log.Fatal(err)
	}
}
