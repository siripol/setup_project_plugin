#!/usr/bin/env bash
# Workspace launch: emit .code-workspace + open in $EDITOR (fallback: code).
# --dry-run: emit file only, never launch.

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="${WORKSPACE_ROOT}/.workspace/registry.json"

if [[ ! -f "${REGISTRY}" ]]; then
  echo "workspace launch: registry.json not found at ${REGISTRY}" >&2
  exit 2
fi

WS_NAME="$(basename "${WORKSPACE_ROOT}")"
OUT_FILE="${WORKSPACE_ROOT}/${WS_NAME}.code-workspace"

# Build folders[] JSON: workspace root first, then each service relative path.
if command -v jq >/dev/null 2>&1; then
  PATHS_JSON=$(jq -r '.services[] | .path' "${REGISTRY}" | awk 'BEGIN { printf "[{\"path\":\".\"}" } { printf ",{\"path\":\"%s\"}", $0 } END { printf "]" }')
else
  PATHS_JSON=$(awk '
    BEGIN { printf "[{\"path\":\".\"}" }
    /"path":/ { gsub(/[",]/, "", $2); printf ",{\"path\":\"%s\"}", $2 }
    END { printf "]" }
  ' "${REGISTRY}")
fi

printf '{\n  "folders": %s\n}\n' "${PATHS_JSON}" > "${OUT_FILE}"
echo "wrote ${OUT_FILE}"

if [[ "${DRY_RUN}" == "1" ]]; then
  exit 0
fi

EDITOR_CMD="${EDITOR:-code}"
if command -v "${EDITOR_CMD}" >/dev/null 2>&1; then
  "${EDITOR_CMD}" "${OUT_FILE}"
else
  echo "launch: no editor found (\$EDITOR unset and 'code' not on PATH); file at ${OUT_FILE}" >&2
fi
