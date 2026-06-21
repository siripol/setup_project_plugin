# Appended to the project Makefile by sn-init for --lang=py.
.PHONY: install fmt lint test mcp-server agent-run client-run req-import-runner safety-runner

install:
	uv sync --all-extras

fmt:
	uv run ruff format src tests scripts

lint:
	uv run ruff check src tests scripts

test:
	uv run pytest

agent-run:
	uv run python src/agent.py

client-run:
	uv run python src/client.py

mcp-server:
	uv run python mcp_server/main.py

# Workflow helpers exposed via the base Makefile delegate to these targets
# so the right interpreter (uv-managed) is used.
req-import-runner:
	uv run python scripts/req_import.py $(FILE)

safety-runner:
	uv run python scripts/safety.py $(ARGS)
