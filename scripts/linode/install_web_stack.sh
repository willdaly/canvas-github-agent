#!/usr/bin/env bash
# Run on the Linode as root after the repo exists at APP_DIR (e.g. post-bootstrap).
# Installs nginx, systemd unit for FastAPI, builds the frontend with VITE_API_URL=/api.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/canvas-github-agent}"
APP_USER="${APP_USER:-canvasagent}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "Expected git checkout at $APP_DIR" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends nginx

sed -e "s|__APP_DIR__|$APP_DIR|g" "$SCRIPT_DIR/nginx-canvas-github-agent.conf" \
  > /etc/nginx/sites-available/canvas-github-agent

if [[ -e /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
fi
ln -sf /etc/nginx/sites-available/canvas-github-agent /etc/nginx/sites-enabled/canvas-github-agent

sed -e "s|__APP_DIR__|$APP_DIR|g" -e "s|__APP_USER__|$APP_USER|g" \
  "$SCRIPT_DIR/canvas-github-agent-api.service.template" \
  > /etc/systemd/system/canvas-github-agent-api.service

systemctl daemon-reload
systemctl enable canvas-github-agent-api.service

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

echo "Web stack installed."
echo "1) Set in $APP_DIR/.env (example):"
echo "     CANVAS_USE_MCP=false"
echo "     SERVICE_BASE_URL=http://YOUR_PUBLIC_IP/api"
echo "     FRONTEND_ORIGINS=http://YOUR_PUBLIC_IP"
echo "2) systemctl status canvas-github-agent-api.service"
echo "3) Open http://YOUR_PUBLIC_IP/"
