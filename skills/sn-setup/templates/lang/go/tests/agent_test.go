package main

import "testing"

// Smoke test placeholder. Replace with real tests once BetaToolRunner is wired.
func TestExampleToolDefinition(t *testing.T) {
	def := exampleToolDefinition()
	if def["name"] != "echo" {
		t.Fatalf("expected name=echo, got %v", def["name"])
	}
}
