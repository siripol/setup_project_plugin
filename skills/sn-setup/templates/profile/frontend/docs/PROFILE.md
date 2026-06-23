# Profile: frontend

`${name}` is scaffolded as a **frontend** — a user-facing web application that renders UI and consumes APIs from one or more backends (typically a BFF).

## Shape

- Owns rendering, interaction, and client-side state. Owns *no* domain data.
- Talks to a BFF (`--profile=bff`) or directly to backend microservices, never to a DB.
- Ships static or hybrid-rendered assets behind a CDN; the running server (if any) handles only SSR / routing.
- Framework selected by `--framework=${framework}` (default `next`). See `docs/FRAMEWORK.md` for framework-specific notes.

## Conventions

- Component library + design tokens live under `src/components/` and `src/design/`.
- Routes are file-based (per framework convention) — Next.js App Router or Vite + React Router.
- Accessibility is non-negotiable; see `docs/ACCESSIBILITY.md`.
- Supported browsers and devices are declared in `docs/BROWSER-MATRIX.md` — anything not on the matrix is best-effort.

## What this profile *isn't*

- A microservice (`--profile=microservice`) — owns a domain.
- A BFF (`--profile=bff`) — aggregates services for *this* frontend.

## Lang

Frontend currently supports `--lang=ts` only. Pure-JS scaffolds are intentionally not supported; types catch a class of UI bugs that's painful to find without them.

## See also

- `docs/FRAMEWORK.md` — framework-specific layout and commands.
- `docs/DESIGN.md` — visual language, tokens, component principles.
- `docs/ACCESSIBILITY.md` — WCAG baseline and per-feature requirements.
- `docs/BROWSER-MATRIX.md` — supported browsers, devices, and degradation rules.
