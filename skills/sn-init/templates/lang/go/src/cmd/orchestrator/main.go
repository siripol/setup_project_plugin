// Tier-2 spec-loop orchestrator wrapper.
//
// Run via `go run ./src/orchestrator.go SPRINT-NNN`. Delegates phase dispatch
// + state persistence to scripts/orchestrator.py and exposes a hook to call
// the Anthropic SDK BetaToolRunner from Go for the subagent invocation.
package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: orchestrator SPRINT-NNN")
		os.Exit(2)
	}
	sprint := os.Args[1]
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		fmt.Fprintln(os.Stderr, "warning: ANTHROPIC_API_KEY not set; subagent calls will stub")
	}

	cmd := exec.Command("python3", "scripts/orchestrator.py", "run", sprint)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// invokeSubagent is the Go-side hook for wiring anthropic-sdk-go BetaToolRunner.
// Today scripts/orchestrator.py owns dispatch; Go callers may use this when
// they need to drive a phase directly without the Python shim.
func invokeSubagent(subagent, prompt string) (map[string]any, error) {
	_ = subagent
	_ = prompt
	return map[string]any{
		"status": "ok",
		"note":   "wire anthropic-sdk-go BetaToolRunner here for live calls",
	}, nil
}
