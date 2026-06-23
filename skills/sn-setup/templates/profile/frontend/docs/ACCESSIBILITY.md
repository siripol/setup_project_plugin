# Accessibility — ${name}

Baseline: **WCAG 2.2 Level AA**. Non-negotiable for any feature that ships to production.

## Minimums

- Every interactive element is reachable, operable, and labeled for keyboard and screen-reader users.
- Visible focus on every interactive element. Never `outline: none` without a replacement.
- Color contrast: 4.5:1 for text under 18pt; 3:1 for text ≥ 18pt and for non-text UI.
- Pages have one and only one `<h1>`. Heading order doesn't skip levels.
- All images carry `alt`. Decorative images use `alt=""` and `aria-hidden="true"`.
- All form fields have labels (visible or `aria-label`). Errors are announced by screen readers.

## Per-component checklist

When you build or change a component, verify:

- [ ] Tab order is logical and matches visual order.
- [ ] All actions work with keyboard alone (Enter / Space / Esc / arrows where appropriate).
- [ ] ARIA roles + properties are correct *or* absent — never both.
- [ ] Live regions announce dynamic content (toasts, errors, loading states).
- [ ] Component passes axe-core with zero violations.
- [ ] Component is screen-reader-tested in at least one of: VoiceOver, NVDA, JAWS.

## Tooling

- `axe-core` runs in unit tests for every component story.
- Lighthouse a11y score is a CI gate; failures block merge.
- Storybook addon-a11y is enabled and configured to fail builds on serious violations.

## What this doesn't cover

- Cognitive accessibility (plain language, predictable flows) — covered in `docs/CONTENT.md` if/when that doc lands.
- Per-locale concerns (RTL layout, locale-specific typography) — track separately when shipping i18n.
