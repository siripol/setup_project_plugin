# .githooks/

Project-local git hooks. Enable once with:

```bash
make hooks-install
```

This runs `git config core.hooksPath .githooks`, so every clone honors them automatically. Re-run after switching branches if the hook scripts change.

| Hook | Behavior |
|---|---|
| `commit-msg` | Rejects commits whose subject doesn't reference a REQ id (`REQ-NNN`), unless the message starts with `chore:`, `wip:`, or `docs:`. |
| `post-merge` | If the merged branch matches `req/REQ-NNN`, runs `make gh-close REQ=REQ-NNN PR=<inferred>` to close the GitHub issue. |
