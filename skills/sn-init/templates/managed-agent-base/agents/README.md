# agents/

Managed Agent YAML configs consumed by the Anthropic CLI (`ant agents apply`). Version-controlled.

- `main.yaml` — primary agent config: model, system prompt, tools, MCP servers, Skills.
- Add per-environment variants here (e.g. `staging.yaml`) and select via `ant agents apply --env staging`.
