#!/usr/bin/env bash
# Policy: branch-naming — reject pushes from non-conforming branches.
set -euo pipefail
BR=$(git rev-parse --abbrev-ref HEAD)
[[ "$BR" == "main" ]] && exit 0
if ! [[ "$BR" =~ ^(feat|fix|chore|docs|refactor|test)/ ]]; then
  echo "branch-naming: branch '$BR' must start with feat/, fix/, chore/, docs/, refactor/, or test/" >&2
  exit 1
fi
