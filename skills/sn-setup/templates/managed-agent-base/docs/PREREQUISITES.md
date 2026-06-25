# Prerequisites — ${name}

Minimum tool + runtime versions required to develop, scaffold, and ship this service. Pinned for reproducibility across machines and CI.

## Required, always

| Tool | Minimum version | Why |
|---|---|---|
| Claude Code | 0.5.x or newer | Slash-command dispatcher, hook execution, plugin marketplace consumer |
| `git` | 2.40 | Templated `.githooks/` (commit-msg gate, post-merge issue closer) |
| `python3` | 3.13 | Plugin scripts (`scripts/*.py`, `sn-setup`) target Python 3.13 |
| `pyyaml` | 6.0 | YAML I/O in `sn-setup` (installed by the plugin's `requirements.txt`) |

## Required per `--lang=`

The scaffold's language overlay sets the runtime baseline.

| `--lang=` | Tool | Minimum |
|---|---|---|
| `go` | `go` | 1.23 |
| `py` | `python3` | 3.13 |
| `py` | `uv` (optional but recommended) | 0.5.x |
| `ts` | `node` | 20.x |
| `ts` | `pnpm` (or `npm`) | 9.x (or 10.x) |

## Required for Tier 3 (Managed Agents)

| Tool | Minimum version | Why |
|---|---|---|
| `ant` CLI | 0.3.x | Managed Agent deploy + validate (`ant agents apply` / `validate`) |

If you scaffolded with `--tier=2`, `ant` is optional.

## How to install

Use a version manager so multiple repos can coexist with different pinned versions:

| Tool | Manager | One-liner |
|---|---|---|
| Language toolchains | `asdf` or `mise` | `asdf install` (reads `.tool-versions`) |
| Node | `nvm` (or via `asdf`/`mise`) | `nvm install 20 && nvm use 20` |
| Python | `pyenv` (or via `asdf`/`mise`) | `pyenv install 3.13 && pyenv local 3.13` |
| Go | `gvm` (or via `asdf`/`mise`) | `gvm install go1.23` |

This scaffold ships a `.tool-versions` file at the repo root. `asdf install` / `mise install` reads it and provisions the right versions automatically.

## Quick verification

```bash
make verify   # runs the scaffold's own check; prints PASS/FAIL per tool above
```

If `make verify` is not yet wired, run the version commands by hand:

```bash
claude --version
git --version
python3 --version
go version          # if --lang=go
node --version      # if --lang=ts
ant --version       # if --tier includes 3
```

## When to bump

Update this file whenever:

- You upgrade a runtime (e.g. moving to Python 3.14) — bump the minimum AND the `.tool-versions` pin in lock-step.
- A plugin dependency tightens its own minimum (e.g. `pyyaml` moves to 7.x). Check the plugin's `requirements.txt`.
- CI starts failing on a previously-passing version — figure out what the floor really is, pin it here, and explain in the commit message.

## See also

- `.tool-versions` — the pin file `asdf`/`mise` actually read.
- `docs/PROMOTION.md` — promoting local skills (also subject to plugin version compatibility).
- Plugin design `§9.2` / `§12.1`.
