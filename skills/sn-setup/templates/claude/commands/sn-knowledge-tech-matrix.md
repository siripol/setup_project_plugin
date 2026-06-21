---
name: sn-knowledge-tech-matrix
description: Regenerate the cross-project tech matrix at <vault>/knowledge/global/tech/README.md.
---

Scans every `<vault>/knowledge/global/tech/<project>/*.md` and emits a markdown table:

```
| Project   | Postgres | Redis | Node | Go   |
|-----------|----------|-------|------|------|
| demo-app  | 16       | 7     | 22   | —    |
| billing   | 14       | 7     | —    | 1.23 |
```

Drift across projects is visible at a glance. Auto-runs at end of each sprint.
