# Framework: Next.js (App Router)

`${name}` uses **Next.js with the App Router** as its frontend framework.

## Layout

```
src/
  app/                # routes, layouts, error boundaries
    layout.tsx        # root layout (fonts, theme provider)
    page.tsx          # home route
    (group)/          # route groups for shared layout without URL effect
  components/         # presentation components (per design tokens)
  features/           # feature folders — colocate data-fetching + UI
  design/             # tokens + theme primitives
  lib/                # framework-agnostic helpers
```

## Rendering

- Prefer **React Server Components** by default. Mark with `"use client"` only when the component needs state, effects, or browser APIs.
- Fetch data in server components (or route handlers) — never in client components when avoidable.
- Stream where it helps perceived latency (`loading.tsx`, `Suspense` boundaries).

## Commands

| Make / npm target | Action |
|---|---|
| `npm run dev` | Local dev server with HMR. |
| `npm run build` | Production build. |
| `npm run start` | Run the production build locally. |
| `npm run lint` | ESLint + type-check. |
| `npm run test` | Unit tests (Vitest or Jest, per repo choice). |

## Conventions

- One feature per folder under `src/features/`.
- Route handlers (`app/.../route.ts`) are thin; business logic lives in `features/` or `lib/`.
- Use Next's `<Image>`, `<Link>`, and `<Script>` components — they exist for measurable reasons.
- Environment variables: client-exposed vars must be prefixed `NEXT_PUBLIC_`; everything else is server-only.

## When to break out of Next

- Need full static export with no SSR? Either use `output: 'export'` or switch to Vite + React (`--framework=vite`).
- Need fine control over Webpack/Vite? Prefer Next's config knobs first; only eject mental-models when there's no other way.
