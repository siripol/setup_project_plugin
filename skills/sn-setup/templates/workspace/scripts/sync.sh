#!/usr/bin/env bash
# Workspace sync: git pull --ff-only across all registered services.
# Skip + warn on dirty working trees; never stash or clobber.

set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="${WORKSPACE_ROOT}/.workspace/registry.json"

if [[ ! -f "${REGISTRY}" ]]; then
  echo "workspace sync: registry.json not found at ${REGISTRY}" >&2
  exit 2
fi

if command -v jq >/dev/null 2>&1; then
  SVC_RAW="$(jq -r '.services[] | "\(.slug)\t\(.path)"' "${REGISTRY}")"
else
  SVC_RAW="$(awk '
    /"slug":/ { gsub(/[",]/, "", $2); slug=$2 }
    /"path":/ { gsub(/[",]/, "", $2); print slug "\t" $2 }
  ' "${REGISTRY}")"
fi

while IFS= read -r line; do
  [[ -z "${line}" ]] && continue
  slug="${line%%	*}"
  rel_path="${line##*	}"
  abs_path="${WORKSPACE_ROOT}/${rel_path}"
  if [[ ! -d "${abs_path}/.git" ]]; then
    echo "skip ${slug}: not a git repo" >&2
    continue
  fi
  dirty_count=$(git -C "${abs_path}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [[ "${dirty_count}" != "0" ]]; then
    echo "skip ${slug}: dirty" >&2
    continue
  fi
  git -C "${abs_path}" fetch --quiet
  if git -C "${abs_path}" pull --ff-only --quiet 2>/dev/null; then
    echo "sync ${slug}: ok"
  else
    echo "skip ${slug}: pull --ff-only failed (non-fast-forward?)" >&2
  fi
done <<< "${SVC_RAW}"
