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

mcp-server:
	go run ./mcp_server
