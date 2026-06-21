# Appended to the project Makefile by sn-init for --lang=go.
.PHONY: install fmt lint test mcp-server agent-run

install:
	go mod tidy

fmt:
	go fmt ./...

lint:
	go vet ./...

test:
	go test ./...

agent-run:
	go run ./src

client-run:
	go run ./src

orchestrator-run:
	go run ./src/cmd/orchestrator $(SPRINT)

mcp-server:
	go run ./mcp_server
