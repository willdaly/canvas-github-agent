# Deploying To Linode (VM Path)

This project is a Python CLI app, so the most reliable deployment target is a Linode VM.

## 1) Create a Linode instance

Run these from your local machine (with Linode CLI already configured):

```bash
linode-cli linodes create \
  --region us-southeast \
  --type g6-standard-2 \
  --image linode/ubuntu24.04 \
  --label canvas-github-agent-prod \
  --root_pass 'CHANGE_ME_TO_A_STRONG_PASSWORD'
```

Capture the returned public IPv4 from the command output.

## 2) Copy the bootstrap script to the VM

From this repository root:

```bash
scp scripts/linode/bootstrap_canvas_agent.sh root@<LINODE_IP>:/root/bootstrap_canvas_agent.sh
ssh root@<LINODE_IP> 'chmod +x /root/bootstrap_canvas_agent.sh'
```

## 3) Run provisioning on the VM

Replace `<REPO_URL>` with your repo URL.

```bash
ssh root@<LINODE_IP> "REPO_URL=<REPO_URL> bash /root/bootstrap_canvas_agent.sh"
```

Example:

```bash
ssh root@<LINODE_IP> "REPO_URL=https://github.com/willdaly/canvas-github-agent.git bash /root/bootstrap_canvas_agent.sh"
```

## 4) Add app secrets on the VM

Create `/opt/canvas-github-agent/.env` with required values:

```env
CANVAS_API_URL=...
CANVAS_API_TOKEN=...
CANVAS_USE_MCP=false
GITHUB_TOKEN=...
GITHUB_USERNAME=...
NOTION_TOKEN=...
NOTION_PARENT_PAGE_ID=...
OPENAI_API_KEY=...
```

Optional hardening: set file ownership and permissions.

```bash
ssh root@<LINODE_IP> "chown canvasagent:canvasagent /opt/canvas-github-agent/.env && chmod 600 /opt/canvas-github-agent/.env"
```

## 5) Verify install and run

Smoke test status:

```bash
ssh root@<LINODE_IP> 'systemctl status canvas-github-agent-smoke.service --no-pager'
```

Interactive run (manual):

```bash
ssh -t root@<LINODE_IP> 'sudo -u canvasagent /opt/canvas-github-agent/.venv/bin/canvas-github-agent-cli'
```

Non-interactive help check:

```bash
ssh root@<LINODE_IP> 'sudo -u canvasagent /opt/canvas-github-agent/.venv/bin/canvas-github-agent --help'
```

## Notes

- The bootstrap script installs Node.js 20 so Smithery/MCP tooling can run.
- For unattended VM deployments, `CANVAS_USE_MCP=false` avoids browser OAuth callback issues.
- If your repo is private, use an authenticated clone URL or configure SSH deploy keys first.
- If you changed branch names, SSH in and run:

```bash
ssh root@<LINODE_IP> 'cd /opt/canvas-github-agent && sudo -u canvasagent git fetch --all && sudo -u canvasagent git checkout deploy/linode'
```
