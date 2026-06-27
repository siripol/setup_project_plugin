---
name: audit-component-coupling
description: Audit React component boundaries in this frontend — prop drilling depth, state hoisting choices, context vs prop usage, component fanout. Outputs per-component coupling score + refactor recommendations. Architecture-focused; distinct from a11y-auditor which checks WCAG conformance.
tools: [Read, Glob, Grep]
---

# Audit component coupling — ${name}

You are auditing this frontend's React component architecture. Your job: surface coupling issues that hurt maintainability — too-deep prop drilling, premature context usage, fanout explosions, state hoisted too high or too low. You read components; you do not modify them.

This skill is **architecture-focused**. WCAG conformance, accessibility patterns, and visual design checks belong to the `a11y-auditor` agent (`.claude/agents/a11y-auditor.md`). Do not duplicate that scope.

## What to audit

For each component in `src/components/` (or the framework's component dir):

### 1. Prop drilling depth

Trace each non-trivial prop (objects, arrays, callbacks — not primitives) from its source to its consumer. The source is the component that introduces the prop into the tree; the consumer is the component that actually reads it.

- Depth 1-3: fine.
- Depth 4-5: flag for review. Could be lifted into context OR the intermediate components could compose differently.
- Depth ≥ 6: critical. The intermediate components are pure forwarders; refactor.

### 2. Context usage

For each `Context.Provider` in the tree:

- How many components consume it? If < 3 OR the consumers all sit in a single subtree of depth ≤ 2, the context is premature; explicit props are cheaper.
- Does the provider's value change frequently? If yes, every consumer re-renders on every change. Flag if the value updates per keystroke (common with form state in context).
- Does the value contain unrelated concerns (auth state + theme + cart)? Split into multiple contexts; consumers only re-render on the slice they care about.

### 3. State hoisting

For each piece of state (`useState`, `useReducer`):

- Where is it declared vs where is it used? If declared 2+ levels above the only consumer, it is hoisted too high.
- If two siblings need the same state, is it hoisted to their common parent? If hoisted higher than necessary, it is hoisted too high.
- If declared in a component that does not use it (only passes it to a child), it is hoisted too high.

### 4. Component fanout

For each component:

- How many children does it render? > 10 children of mixed types suggests the component is a layout grab-bag; consider splitting by concern.
- How many props does it accept? > 8 props suggests the component is overloaded; consider splitting into specialized variants.
- How many other components does it import? > 12 component imports suggests the file is doing too much.

## How to find components

Start with `Glob` on `src/components/**/*.{tsx,jsx,ts,js}` or the framework's component dir. For each component file, use `Read` to inspect:

- The component's prop type / interface (top of file).
- The JSX it returns (`return (...)`).
- The hooks it calls (`useState`, `useReducer`, `useContext`, custom hooks).

For prop drilling traces, use `Grep` to find consumers of a prop name across the codebase.

## Output format

```
| Component | Depth (max prop drilling) | Context use | State hoisting | Fanout | Coupling score | Notes |
|---|---|---|---|---|---|---|
| SidebarPanel | 6 (settings → nav → user) | ✅ ThemeContext | ⚠ filter state declared 2 levels above use | 4 children | 14 | Refactor: hoist filter state down; settings → nav passes 4 props transparently. |
| HeaderBar | 2 | none | ✅ local | 6 children | 4 | Healthy. |

Summary:
- Components audited: <N>
- Healthy (score ≤ 6): <N>
- Review (score 7-12): <N>
- Refactor (score ≥ 13): <N>
- Top 3 refactor candidates: <list>
```

Coupling score: `prop_drilling_depth + (context_consumers / 3) + (state_hoist_levels * 2) + (fanout / 3)`. Lower is better.

## What NOT to do

- Do not modify code. Output is an audit only.
- Do not flag WCAG, ARIA, or color-contrast issues — that is `a11y-auditor`'s job.
- Do not flag bundle size, render performance, or memoization issues — that is profiling territory, not coupling.
- Do not score components from third-party libraries (`node_modules`).
- Do not generalize: each finding cites a specific component file.

## See also

- `.claude/docs/frontend-conventions.md` — the conventions this skill checks against (Component composition + State management discipline sections).
- `.claude/agents/a11y-auditor.md` — companion accessibility-focused review; runs on every UI-touching PR.
