# Appended to the project Makefile by sn-init for --lang=py.
.PHONY: install fmt lint test mcp-server agent-run

install:
	uv sync --all-extras

fmt:
	uv run ruff format src tests

lint:
	uv run ruff check src tests

test:
	uv run pytest

agent-run:
	uv run python src/agent.py

mcp-server:
	uv run python mcp_server/main.py
