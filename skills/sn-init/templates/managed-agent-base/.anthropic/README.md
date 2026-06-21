# .anthropic/

Rarely-touched Anthropic config. Grouped here to keep the project root clean.

Reserved subdirs (create as needed):

- `vaults/` — credential Vault configs (`client.beta.vaults.*`).
- `memory_stores/` — Memory Store configs.
- `deployments/` — scheduled deployment YAML for cron-driven agents.
- `tools/` — custom tool definitions (schema + handler refs).
- `scripts/` — helper scripts (e.g. `create_agent.sh`, `run_session.sh`).
