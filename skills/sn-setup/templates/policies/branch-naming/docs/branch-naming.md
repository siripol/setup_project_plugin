# Policy — Branch naming

Pre-push hook rejects pushes from branches whose name doesn't match one of:

- `feat/<slug>`
- `fix/<slug>`
- `chore/<slug>`
- `docs/<slug>`
- `refactor/<slug>`
- `test/<slug>`

`main` is always allowed. Override per push with `git push --no-verify` (not
recommended).
