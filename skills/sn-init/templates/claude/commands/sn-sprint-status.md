---
name: sn-sprint-status
description: Print a table of every sprint (active + completed) with REQ counts, status, owner, and last update.
---

Scans `docs/sprints/active/` + `docs/sprints/completed/`. Output:

```
SPRINT    SLUG          STATUS     REQs  COMPLETED  OWNER
001       auth-rev      running    3     1/3        alice
002       billing       planning   2     0/2        bob
```
