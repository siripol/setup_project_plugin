# init-project-plugin

Claude Code plugin shipping the `sn-init` skill — scaffold Claude-powered projects (Tier 2 Agent SDK + Tier 3 Managed Agents) following Anthropic conventions and OpenAI harness engineering principles.

## Install

```bash
claude plugin install /path/to/init_project_plugin
```

Or point Claude Code at the directory directly.

## Commands

- `/sn-init [name] [flags]` — auto-detects mode from current directory:
  - **new mode** (empty cwd or `name` given): full project scaffold + git init.
  - **add mode** (non-empty cwd, no `name`): writes only `.claude/` (idempotent patch).

## Quickstart

```bash
mkdir my-agent && cd my-agent
/sn-init demo                  # default lang=go, tier=both, workflow=spec-loop
cd demo
make agent                     # ant agents apply agents/main.yaml
make session                   # start a Managed Agent session
```

## Flag reference

See `commands/sn-init.md` for the full flag table. Highlights:

| Flag | Default | Purpose |
|---|---|---|
| `--lang` | `go` | Stack overlay: `go`, `py`, `ts` |
| `--tier` | `both` | Anthropic tier: `2` (Agent SDK), `3` (Managed Agents), `both` |
| `--no-git` | git on | Skip `git init` + first commit |
| `--install` | off | Run dep install + `ant agents apply` after scaffold |
| `--no-ci` | CI on | Skip `.github/workflows/ci.yml` |
| `--devcontainer` | off | Write `.devcontainer/devcontainer.json` |
| `--obsidian[=PATH]` | on | Obsidian tracking note (default vault → `<target>/docs/exec-plans/active/`) |
| `--prompt="..."` | placeholder | Seed `agents/main.yaml` system block |
| `--workflow` | `spec-loop` | Bundle spec-driven dev loop |
| `--dry-run` | off | Print file tree, no FS writes |
| `--verbose` | off | Per-step log to `.sn-init.log` |

## Development

```bash
# run plugin self-tests
pytest tests/

# scaffold to a temp dir for manual check
python3 scripts/sn_init.py /tmp/snitest-demo --dry-run
```

## License

MIT — see `LICENSE`.
