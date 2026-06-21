# Appended to the project Makefile by sn-init for --lang=ts.
.PHONY: install fmt lint test mcp-server agent-run client-run build

install:
	npm install

fmt:
	npx prettier --write "src/**/*.ts" "mcp_server/**/*.ts" "tests/**/*.ts" ".claude/hooks/*.ts"

lint:
	npx tsc --noEmit

test:
	npm test

build:
	npm run build

agent-run:
	npm run agent

client-run:
	npm run client

orchestrator-run:
	npm run orchestrator -- $(SPRINT)

mcp-server:
	npm run mcp-server
