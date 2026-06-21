# .harness/

Repo-resident harness engineering config per OpenAI's framework. Human-edit only — agents may read these files but should not modify them without an explicit REQ + human gate.

| Path | Purpose |
|---|---|
| `rules/` | Custom lint rules. Each rule's error message includes correction instructions injected into the agent's context. |
| `invariants/` | Architectural invariants + tests that verify them. `make check-invariants` runs all. |
| `normal-forms/` | Allowed and forbidden shapes per component kind (subagent, MCP server, skill). |
| `chokepoints.yaml` | Critical files that require a human gate before modification. PreToolUse hook reads this. |
| `proof-bundle-template.md` | Template for `docs/sprints/completed/SPRINT-*/proof/PLAN-*.proof.md`. |

## Principles applied

1. Repository-resident knowledge
2. Executable architecture (rules + invariants compile to gates)
3. Scarcity inversion (review > generation)
4. Context bundles (per-TASK files)
5. Repair-shape proportionality (local repairs only)
6. Graph substrate (`docs/generated/dep-graph.md`)
7. Bounded authority (per-subagent capability manifest)
8. Runtime legibility (`.sn-init/logs/`)
9. Adversarial testing (`sn:adversary` subagent)
10. No-good compilation (failures → rules)
11. Semantic density
12. Invariant coverage
13. Capability manifest
14. Choke-point protection (`chokepoints.yaml`)
15. Proof bundles
16. Nested feedback loops
17. Intervention geometry
18. Engineering normal form
