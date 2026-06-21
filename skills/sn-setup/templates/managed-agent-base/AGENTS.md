# ${name} — Agent map

This file is a short (≤100 lines) context map for agents (Claude, Codex, Cursor). Treat it as a map, not the destination — follow the pointers below.

## Project goal

(One paragraph: what this agent does, who it serves, the outcome.)

## Where to look

| Topic | Path |
|---|---|
| Architecture | `docs/design-docs/index.md` |
| Design principles | `docs/principles/design.md` |
| Roadmap / plans | `docs/principles/plans.md` |
| Quality bar | `docs/principles/quality.md` |
| Reliability + SLO | `docs/principles/reliability.md` |
| Security | `docs/principles/security.md` |
| Product sense | `docs/principles/product-sense.md` |
| Subagent library | `docs/design-docs/subagents.md` |
| Active requirements | `docs/requirements/active/` |
| Active sprints | `docs/sprints/active/` |
| Vendor docs (LLM context) | `docs/references/*-llms.txt` |
| Local notes | `CLAUDE.local.md` (gitignored) |
| Audit log | `.sn-init/logs/exec-*.jsonl` |

## Key invariants

- Default model: `${model}` with `thinking: {type: "adaptive"}`.
- Token budget per session: 200k (see `agents/main.yaml`).
- Chokepoint files (forced human gate before edit): see `.harness/chokepoints.yaml`.

## How to run

```bash
make agent          # ant agents apply agents/main.yaml
make session        # ant sessions create --agent-id $AGENT_ID
make test           # per-lang test suite
make validate       # ant agents validate
```

## Owners

(Add owner names + contacts here.)
