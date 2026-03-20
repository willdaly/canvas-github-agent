#!/usr/bin/env bash
# Run on the Linode as root to pull latest main and rebuild/restart the web stack.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/canvas-github-agent}"
APP_USER="${APP_USER:-canvasagent}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

sudo -u "$APP_USER" bash -lc "
  set -euo pipefail
  cd '$APP_DIR'
  git fetch --all --prune
  git checkout main 2>/dev/null || git checkout master
  git pull --ff-only
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  pip install -q -e .
  cd frontend
  npm ci
  VITE_API_URL=/api npm run build
"

nginx -t
systemctl reload nginx
systemctl restart canvas-github-agent-api.service

echo "Updated and restarted canvas-github-agent-api."
