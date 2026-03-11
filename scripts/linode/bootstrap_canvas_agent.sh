#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script for deploying canvas-github-agent on an Ubuntu Linode.
# Required env vars:
#   REPO_URL (https URL to this git repo)
# Optional env vars:
#   APP_DIR (default: /opt/canvas-github-agent)
#   APP_USER (default: canvasagent)

REPO_URL="${REPO_URL:-}"
APP_DIR="${APP_DIR:-/opt/canvas-github-agent}"
APP_USER="${APP_USER:-canvasagent}"

if [[ -z "$REPO_URL" ]]; then
  echo "REPO_URL is required. Example:"
  echo "  REPO_URL=https://github.com/willdaly/canvas-github-agent.git bash bootstrap_canvas_agent.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  python3 \
  python3-venv \
  python3-pip \
  git \
  ca-certificates \
  curl \
  gnupg

mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
  | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
  > /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y --no-install-recommends nodejs

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

mkdir -p "$(dirname "$APP_DIR")"
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

sudo -u "$APP_USER" bash -lc "
  set -euo pipefail
  cd '$APP_DIR'
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  pip install -e .
"

cat > /etc/systemd/system/canvas-github-agent-smoke.service <<EOF
[Unit]
Description=Canvas GitHub Agent smoke test
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=-$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/canvas-github-agent --help

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable canvas-github-agent-smoke.service
systemctl start canvas-github-agent-smoke.service

echo "Bootstrap complete."
echo "Next steps:"
echo "1) Put secrets in $APP_DIR/.env"
echo "2) For non-interactive servers, set CANVAS_USE_MCP=false in .env"
echo "3) Test interactive mode: sudo -u $APP_USER $APP_DIR/.venv/bin/canvas-github-agent-cli"
echo "4) Check smoke service: systemctl status canvas-github-agent-smoke.service"
