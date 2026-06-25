# Architecture — ${name}

Load-on-demand architecture overview. The service team fills this in; Claude reads when work crosses an architectural boundary.

## Quick map

(Replace this section with a 5–10 line summary of what this service does and how it's shaped.)

## Components

- (List the top-level components / modules.)
- (One line per component: its job, its inputs, its outputs.)

## Data flow

(One paragraph or one diagram. Where does data enter? Where does it leave? What transformations happen in between?)

## External dependencies

(See also the `## Repository Ecosystem` table in `CLAUDE.md` for cross-service relationships.)

- (Per downstream: what we call, why, fallback strategy.)
- (Per upstream caller: what they ask of us, SLA.)

## Architectural decisions

Treat this as a lightweight ADR log. Per decision:

```
### YYYY-MM-DD: <one-line decision>
- Context: <why a decision was needed>
- Choice: <what we picked>
- Alternatives: <what we rejected, briefly>
- Cost: <what this choice makes harder>
```

## Anti-patterns

(Patterns explicitly off-limits in this service. Cross-link to `[[anti-patterns/<name>]]` in the Obsidian vault when relevant.)

## See also

- `../../CLAUDE.md` — always-on top-level.
- `../rules/README.md` — always-on hard rules.
- `../../docs/PROMOTION.md` — when an internal pattern earns marketplace promotion.
- Plugin design `§5.3`.
