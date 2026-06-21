# Sprint template

To create a sprint:

```bash
make sprint-new SLUG=<slug>
```

This creates `docs/sprints/active/SPRINT-NNN-<slug>/` with the directory layout:

```
SPRINT-NNN-<slug>/
  sprint.md            # manifest (goal, REQs list, status, owner)
  requirements/        # REQs mv'd from docs/requirements/active/
  exec-plans/          # planner output
  tasks/               # task-decomposer output
  proof/               # PLAN-NNN.proof.md after completion
  impact.md            # impact-analyzer pre-run report
```

A `sprint.md` looks like:

```markdown
---
id: SPRINT-NNN
title: ...
status: planning   # planning | ready | running | completed
reqs: []           # REQ ids
goal: one-line outcome
owner: ...
created_at: YYYY-MM-DD
---

## Goal

What this sprint delivers when complete.

## REQs in scope

(Filled by `make sprint-add SPRINT=... REQ=...`)

## Out of scope

What deliberately NOT in this sprint.
```
