// Tier 3 — Managed Agents session driver.
//
// Stubs the call to client.beta.Sessions.New. Replace the placeholder with the
// real SDK calls once anthropic-sdk-go is pulled in (`make install`).
package main

import (
	"context"
	"fmt"
	"log"
	"os"
)

func RunSession(agentID string) {
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		log.Fatal("set ANTHROPIC_API_KEY in env")
	}
	if agentID == "" {
		log.Fatal("set AGENT_ID in env or pass -agent-id flag")
	}
	ctx := context.Background()
	_ = ctx
	// Pseudocode:
	//   client := anthropic.NewClient()
	//   session, err := client.Beta.Sessions.New(ctx, anthropic.BetaSessionNewParams{
	//       AgentID: anthropic.F(agentID),
	//   })
	//   if err != nil { log.Fatal(err) }
	//   for event := range client.Beta.Sessions.EventStream(ctx, session.ID) {
	//       handle(event)
	//   }
	fmt.Printf("client.go stub. Wire up client.Beta.Sessions.New for agent %s.\n", agentID)
}
