.PHONY: help agent session test fmt lint validate logs-tail logs-clean logs-stats mcp-server

help:
	@echo "make agent      — ant agents apply agents/main.yaml"
	@echo "make session    — ant sessions create --agent-id $$AGENT_ID"
	@echo "make test       — lang test suite"
	@echo "make fmt        — format"
	@echo "make lint       — lint"
	@echo "make validate   — ant agents validate"
	@echo "make logs-tail  — tail audit log"
	@echo "make logs-clean — delete audit logs older than 30 days"
	@echo "make logs-stats — count tool calls + token usage per session"
	@echo "make mcp-server — start project-local MCP server"

agent:
	ant agents apply agents/main.yaml

session:
	@if [ -z "$$AGENT_ID" ]; then echo "AGENT_ID env var not set"; exit 1; fi
	ant sessions create --agent-id $$AGENT_ID

validate:
	ant agents validate agents/main.yaml

logs-tail:
	@mkdir -p .sn-init/logs
	@tail -F .sn-init/logs/exec-*.jsonl 2>/dev/null | (command -v jq >/dev/null && jq . || cat)

logs-clean:
	@find .sn-init/logs -name 'exec-*.jsonl' -mtime +30 -delete 2>/dev/null || true

logs-stats:
	@if ! command -v jq >/dev/null; then echo "jq required"; exit 1; fi
	@for f in .sn-init/logs/exec-*.jsonl; do \
		[ -f "$$f" ] || continue; \
		echo "$$f"; \
		jq -s 'group_by(.tool_name) | map({tool: .[0].tool_name, count: length, in: (map(.usage.input_tokens // 0) | add), out: (map(.usage.output_tokens // 0) | add)})' "$$f"; \
	done

# Lang-specific targets live in Makefile.<lang> (e.g. Makefile.go) and are merged here.
-include Makefile.*
