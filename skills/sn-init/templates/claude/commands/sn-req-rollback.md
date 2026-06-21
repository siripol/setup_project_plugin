---
name: sn-req-rollback
description: Reset the working tree to the pre-REQ-NNN git snapshot tag. Discards any commits made for that REQ.
args:
  - REQ (required) — REQ id (e.g. REQ-003)
---

`git reset --hard $(git tag | grep ^sn-init/pre-${REQ}- | sort -r | head -1)`. Aborts if no matching tag.

Use after a failed sprint to start fresh from the pre-REQ baseline.
