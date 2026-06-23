# Policy — Commit-msg gate

Subjects must match one of:

- `REQ-NNN: <text>` for a ticket-tracked change.
- `<type>(<scope>?): <text>` where `<type>` ∈ `{feat, fix, chore, docs, refactor, test, perf, build, ci, style, revert}` (Conventional Commits).

Wraps `.githooks/commit-msg`. If the hook already exists, this policy adds
its own line and exits 0 from the policy's wrapper when the inner script
passes.
