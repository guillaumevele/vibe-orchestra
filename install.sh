#!/usr/bin/env bash
# vibe-orchestra installer — makes plain `vibe` a Mistral orchestrator.
#
#   ./install.sh                 install (idempotent)
#   ./install.sh --uninstall     remove everything it added
#   IOS_KIT=/path ./install.sh   point at your vibe-ios-kit checkout
#
# Edits ~/.vibe in place — but idempotently, only inside marked blocks / the
# managed mcp_servers array, and after backing up the files it touches.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIBE_HOME="${HOME}/.vibe"
IOS_KIT="${IOS_KIT:-${REPO_DIR}/../vibe-ios-kit}"

# The config surgery runs on vibe's own interpreter (3.11+, has tomllib).
PY="$(command -v vibe >/dev/null 2>&1 && dirname "$(command -v vibe)")/python"
[ -x "$PY" ] || PY="python3"

if [ "${1:-}" = "--uninstall" ]; then
  "$PY" -m vibe_orchestra.install --uninstall --vibe-home "${VIBE_HOME}" 2>/dev/null \
    || PYTHONPATH="${REPO_DIR}" "$PY" -m vibe_orchestra.install --uninstall --vibe-home "${VIBE_HOME}"
  exit 0
fi

echo "Installing vibe-orchestra into ${VIBE_HOME}…"

# 1. Ensure the MCP CLIs exist (isolated, like vibe itself).
if ! command -v vibe-fim-mcp >/dev/null 2>&1; then
  command -v uv >/dev/null 2>&1 && uv tool install "vibe-fim[mcp]" >/dev/null \
    || echo "  NOTE: run  pip install \"vibe-fim[mcp]\""
fi
if ! command -v vibe-orchestra-mcp >/dev/null 2>&1; then
  command -v uv >/dev/null 2>&1 && uv tool install "${REPO_DIR}" --with "mcp>=1.2" >/dev/null \
    || echo "  NOTE: run  pip install \"${REPO_DIR}[mcp]\""
fi

# 2. Wire ~/.vibe (posture + global MCP + iOS specialist).
PYTHONPATH="${REPO_DIR}" "$PY" -m vibe_orchestra.install \
  --vibe-home "${VIBE_HOME}" --repo "${REPO_DIR}" --ios-kit "${IOS_KIT}"

cat <<EOF

Installed. Now, anywhere:

  vibe "round the body of computeScore() to 2 decimals, leave the rest"
  vibe "add a shimmer Metal loader to onboarding, gated on scenePhase"

Plain \`vibe\` now routes: it calls route() to pick the model/specialist, and
edits via surgical_patch (Codestral FIM). Inspect the policy with:

  vibe-orchestra routes

Undo with:  ./install.sh --uninstall
EOF
