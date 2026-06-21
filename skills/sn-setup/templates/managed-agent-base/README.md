# ${name}

Claude-powered project scaffolded by **sn-setup** (Tier 2 Agent SDK + Tier 3 Managed Agents).

## Folder map

| Path | Purpose |
|---|---|
| `AGENTS.md` | ≤100-line cross-tool context map |
| `CLAUDE.md` | Root memory (committed) — auto-loaded by Claude Code + Agent SDK |
| `CLAUDE.local.md` | Local-only memory (gitignored) |
| `agents/main.yaml` | Managed Agent config for `ant` CLI |
| `environments/default.yaml` | Per-env vars + secret refs |
| `mcp/mcp.json` | MCP server registry |
| `skills/example-skill/` | Project-local Skills (Skills API) |
| `.anthropic/` | Rarely-touched config (vaults, memory_stores, deployments, tools) |
| `src/agent.*` | Tier 2 — local agent loop |
| `src/client.*` | Tier 3 — Managed Agents session driver |
| `mcp_server/main.*` | Runnable MCP server stub |
| `tests/` | Per-lang smoke tests |
| `docs/principles/` | Design / plans / quality / reliability / security / product-sense |
| `docs/design-docs/` | Architecture + invariants + subagent index |
| `docs/requirements/active/` | Unassigned requirements awaiting sprint assignment |
| `docs/sprints/active/SPRINT-N-*/` | One folder per active sprint (REQ + plans + tasks + proof inside) |
| `docs/references/*-llms.txt` | Vendor docs ingested for LLM context |
| `.claude/` | Claude Code + Agent SDK auto-load source |
| `.sn-init/` | Runtime state + audit logs (gitignored) |

## Quickstart

```bash
cp .env.example .env                # fill in ANTHROPIC_API_KEY
make agent                          # ant agents apply agents/main.yaml
export AGENT_ID=<id-from-output>
make session
```

## Local agent loop (Tier 2)

```bash
# go
go run ./src/agent.go

# py
uv run src/agent.py

# ts
npm run agent
```

## Audit log

Every Claude call writes a JSONL record to `.sn-init/logs/exec-*.jsonl`. Read it with:

```bash
make logs-tail        # follow live
make logs-stats       # tool + token summary
```

## Agent ID

(Populated by `make agent` / `--install`.)

## License

(See `LICENSE` if present.)
