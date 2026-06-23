# Design — ${name}

How the UI looks, feels, and stays consistent.

## Design tokens

Tokens are the single source of truth for visual values. Live under `src/design/tokens/`.

| Token group | Examples |
|---|---|
| Color | `--color-bg-default`, `--color-fg-muted`, `--color-accent-primary` |
| Spacing | `--space-1` (4px), `--space-2` (8px), … `--space-12` (96px) |
| Typography | `--font-sans`, `--font-mono`, `--text-sm`, `--text-base`, `--text-lg`, … |
| Radii | `--radius-sm`, `--radius-md`, `--radius-lg` |
| Elevation | `--shadow-card`, `--shadow-modal` |
| Motion | `--duration-fast`, `--duration-base`, `--ease-out` |

Components consume tokens. Components never hard-code raw values.

## Components

- One folder per component under `src/components/<Name>/`.
- Each folder ships: the component, a Storybook story, and a unit test.
- Components are presentation-only by default; data-fetching wrappers live in `src/features/`.
- Composition over configuration — prefer many small components to one mega-component with 14 boolean props.

## Theming

- Light/dark mode by default. Theme is applied via CSS variables on `:root`.
- System preference is the initial theme; users can override and persist their choice.
- Test every component in both themes before merge.

## Iconography

- One icon set. Inline SVGs or a single icon font — pick one, stick with it.
- Icons inherit `currentColor`; never hard-code colors on icons.

## Imagery

- Use the framework's image component for static images (`<Image>` in Next, plugin in Vite). Hand-rolled `<img>` is the exception, not the rule.
- All images carry `alt` text. Decorative images use `alt=""` and `aria-hidden="true"`.

## Anti-patterns

- Inline styles for layout (use tokens + utility classes or CSS modules).
- One-off colors that don't go through tokens.
- "Just this once" deviations from the type scale.
- Components that mix data-fetching and rendering at the leaf level.
