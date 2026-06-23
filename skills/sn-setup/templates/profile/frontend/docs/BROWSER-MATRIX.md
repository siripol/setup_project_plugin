# Browser Matrix — ${name}

Where `${name}` is supported, where it degrades, and where it doesn't run at all.

## Supported (full fidelity)

| Browser | Versions | Platforms |
|---|---|---|
| Chrome | last 2 stable | desktop, Android |
| Safari | last 2 stable | macOS, iOS |
| Firefox | last 2 stable | desktop |
| Edge | last 2 stable | desktop |

"Full fidelity" means: all features work, visual polish is intact, no known regressions.

## Degraded (works, not pretty)

| Browser | Versions | What degrades |
|---|---|---|
| Chrome | 3rd-to-last stable | Visual polish; non-critical animations may drop |
| Safari | 3rd-to-last stable | Same as Chrome |

Degraded environments must still allow users to complete primary flows.

## Not supported

| Browser | Versions | Behavior |
|---|---|---|
| IE | any | Show "browser-unsupported" page on entry |
| Pre-2-year browsers | — | Best-effort; we don't QA |

## Devices

- Mobile (≥ 360px wide, modern Android + iOS): primary target alongside desktop.
- Tablet (768–1024px): supported, design QA per release.
- Desktop (≥ 1280px): primary target.
- Foldables / unusual aspect ratios: best-effort.

## Update policy

Bump the matrix in lock-step with browser releases. Major version drops (e.g. dropping support for a previously-listed browser) require a notice in `CHANGELOG.md`.
