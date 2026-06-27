# Frontend conventions — ${name}

Long-form reference for typical frontend topics that apply across Next.js and Vite stacks: component composition, accessibility (high-level), state management discipline, performance budgets, testing strategies. Claude reads this on demand when work touches components, hooks, routing, or build configuration. Always-on rules live in `.claude/rules/` instead.

For framework-specific guidance (Next.js routing, Vite build config), see `docs/FRAMEWORK.md` shipped by the `--framework=` overlay. For WCAG 2.2 AA conformance details (alt text, focus management, ARIA, color contrast), see the `a11y-auditor` agent at `.claude/agents/a11y-auditor.md`.

## Component composition

### Boundaries by concern, not by file size

Components split along a single axis: one concern, one component. The concern can be data-fetching, presentation, layout, or interaction — but each component owns one. Splitting purely because a file grew large produces components that share state and props but no semantic boundary; that is worse than the original large file.

When deciding to split:

- Does the new component have a name that describes its purpose without referencing its parent? If not, the split is mechanical, not semantic — keep the original.
- Will any consumer use the new component without its sibling(s)? If not, the split adds cost without reuse benefit.
- Does the new component own its own state, or only forward props? Pure forwarders are usually a sign that the split happened too eagerly.

### Container vs presentation

The container/presentation distinction (smart vs dumb components) is a useful first cut but not a hard rule. Modern hooks-based code often blurs the line — a single component does both data fetching and rendering. That is fine when the component's purpose is "show this thing"; it becomes a problem when the component grows to "show this thing AND that other thing AND handle this side effect."

### Props vs context

| Pattern | When to use |
|---|---|
| Explicit props | The state is used by 1-3 components in a single subtree. Default choice. |
| React Context | The state is used by 5+ components OR crosses 3+ levels of the tree. |
| External state (Redux, Zustand, etc.) | The state spans multiple unrelated subtrees OR persists across navigation OR has complex update logic worth isolating from React's render lifecycle. |

Prop drilling becomes a real problem only at depth ≥ 4. Below that, prop drilling is cheaper than context — it is explicit, refactorable, and does not trigger re-renders for components that don't use the value.

## Accessibility (high-level)

WCAG 2.2 AA conformance details live in the `a11y-auditor` agent. The conventions below are the always-true patterns:

- Every interactive element is reachable by keyboard.
- Focus is visible. The default browser focus ring is acceptable; custom focus styles must be at least as prominent.
- Semantic HTML is the default. `<button>` for actions, `<a>` for navigation, `<form>` for submission. Use ARIA only when semantic HTML cannot express the pattern.
- Images and icons that convey meaning have non-empty `alt` attributes. Decorative images have `alt=""` (not omitted).
- Color is never the only signal. Pair color with text, icon, or pattern.

Run the `a11y-auditor` agent on every PR that touches UI components.

## State management discipline

### Local first, lifted when shared

Component-local state (`useState`, `useReducer`) is the default. Lift state to the nearest common ancestor only when two or more siblings need to read or write it.

### Server state separated from UI state

Server state (data fetched from a backend) has different lifecycle requirements than UI state (form drafts, modal open/closed, accordion expanded). Use a server-state library (TanStack Query, SWR) for the former; component state or context for the latter. Mixing the two produces bugs where stale UI state survives a refetch.

### Avoid global mutable singletons

Even outside React, do not export mutable state from modules. Singletons make testing harder, hide dependencies, and produce render-cycle bugs that are nearly impossible to reproduce.

## Performance budgets

### Bundle size targets

| Bundle | Initial load budget | Per-route budget (lazy) |
|---|---|---|
| Main JS | ≤ 250 KB gzipped | ≤ 100 KB gzipped per route |
| Main CSS | ≤ 50 KB gzipped | ≤ 20 KB gzipped per route |
| Critical fonts | ≤ 100 KB total | n/a |

Routes that exceed the budget warrant code-splitting. Bundles that exceed the budget AFTER splitting warrant a hard look at dependencies: is this dependency really worth the size?

### Render performance

- Memoize expensive computations with `useMemo`; do NOT memoize cheap computations (the memoization overhead exceeds the recompute cost).
- Use `React.memo` on components that render frequently with identical props.
- Avoid passing fresh object/array/function references as props on every render. Use `useMemo` / `useCallback` to stabilize them when the consumer is memoized.
- Profile before optimizing. The React DevTools Profiler is the source of truth.

### Image and font handling

- Images use modern formats (WebP, AVIF) with fallbacks. Specify width + height to prevent layout shift.
- Fonts use `font-display: swap` (or `optional` for non-critical fonts). Preload critical fonts.
- Lazy-load below-the-fold images. The browser's native `loading="lazy"` is sufficient for most cases.

## Testing strategies

### Unit tests

Test components in isolation with React Testing Library. Assert on what the user sees and does, not on implementation details (state values, instance methods).

```
expect(screen.getByRole('button', { name: 'Submit' })).toBeEnabled()
fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
expect(await screen.findByText('Submitted')).toBeInTheDocument()
```

### Integration tests

Test component graphs end-to-end with the same framework. Mock at the network boundary (MSW for HTTP, mock the WebSocket transport). Do not mock React internals.

### E2E tests

Playwright (preferred) or Cypress for cross-browser flows. Run in CI on every PR that touches routing or auth. Smoke-test the critical paths (login, checkout, dashboard) on every push to main.

### Visual regression

Optional. Useful when the design team is large enough to enforce visual standards; expensive to maintain when the design changes rapidly.

## See also

- `.claude/agents/a11y-auditor.md` — WCAG 2.2 AA conformance agent (B2.1c). Dispatched on every UI-touching PR.
- `.claude/skills/example-frontend/SKILL.md` — `audit-component-coupling` skill; companion architecture-focused audit.
- `docs/FRAMEWORK.md` — framework-specific guidance (Next.js routing, Vite config) per `--framework=`.
- `docs/ACCESSIBILITY.md`, `docs/DESIGN.md`, `docs/BROWSER-MATRIX.md`, `docs/PROFILE.md` — profile-level docs.
