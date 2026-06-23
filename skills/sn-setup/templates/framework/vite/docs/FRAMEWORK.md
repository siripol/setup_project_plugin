# Framework: Vite + React

`${name}` uses **Vite + React** as its frontend framework. SPA-shaped; no SSR.

## Layout

```
src/
  main.tsx            # entry: mount <App /> into #root
  App.tsx             # top-level router + providers
  routes/             # route components (per React Router or TanStack Router)
  components/         # presentation components (per design tokens)
  features/           # feature folders — colocate data-fetching + UI
  design/             # tokens + theme primitives
  lib/                # framework-agnostic helpers
index.html            # template; lives at the repo root, not under src/
vite.config.ts        # Vite config
```

## Rendering

- Client-side only. All rendering happens in the browser.
- Use code-splitting (dynamic `import()`) on heavy routes; Vite handles the rest.
- Suspense boundaries are still useful for data-loading patterns (TanStack Query, etc.).

## Commands

| Make / npm target | Action |
|---|---|
| `npm run dev` | Vite dev server with HMR. |
| `npm run build` | Production build → `dist/`. |
| `npm run preview` | Serve the built `dist/` locally for smoke-testing. |
| `npm run lint` | ESLint + type-check. |
| `npm run test` | Unit tests (Vitest). |

## Conventions

- One feature per folder under `src/features/`.
- Routing: pick **one** router (React Router or TanStack Router) and stick with it.
- Environment variables: client-exposed vars must be prefixed `VITE_`.
- Static assets in `public/` are served at the URL root verbatim; anything imported through `src/` goes through Vite's pipeline.

## When to break out of Vite

- Need SSR / RSC / streaming? Switch to Next.js (`--framework=next`).
- Need framework-agnostic build for a library? Use Vite's library mode (`build.lib`) or `tsup` — not a frontend app shape.
