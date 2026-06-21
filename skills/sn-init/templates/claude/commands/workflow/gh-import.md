---
name: gh-import
description: Pull GitHub issues labeled `req` into docs/requirements/active/ as REQ-NNN files.
---

Runs `gh issue list --label req --state open --json number,title,body` and converts each issue into a REQ scaffold:

- Title → REQ title
- Body bullets → acceptance criteria
- Issue number → REQ id suffix
- Label set → priority hint

Requires `gh` CLI authenticated. Paired with `--workflow-pr` + `/gh-close` for auto-close on merge.
