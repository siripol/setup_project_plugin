#!/usr/bin/env bash
# Workspace status: print one line per registered service.
# Format: slug=<X> branch=<B> ahead=<N> behind=<N> dirty=<N>

set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="${WORKSPACE_ROOT}/.workspace/registry.json"

if [[ ! -f "${REGISTRY}" ]]; then
  echo "workspace status: registry.json not found at ${REGISTRY}" >&2
  exit 2
fi

# Parse services array: prefer jq, fallback to awk.
if command -v jq >/dev/null 2>&1; then
  SVC_RAW="$(jq -r '.services[] | "\(.slug)\t\(.path)"' "${REGISTRY}")"
else
  # awk fallback: parse slug + path pairs from the services array.
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
    echo "slug=${slug} branch=? ahead=0 behind=0 dirty=0 missing=1"
    continue
  fi
  branch=$(git -C "${abs_path}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
  ahead_behind=$(git -C "${abs_path}" rev-list --left-right --count "@{upstream}...HEAD" 2>/dev/null || echo "0	0")
  behind="${ahead_behind%%	*}"
  ahead="${ahead_behind##*	}"
  dirty=$(git -C "${abs_path}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  echo "slug=${slug} branch=${branch} ahead=${ahead} behind=${behind} dirty=${dirty}"
done <<< "${SVC_RAW}"
