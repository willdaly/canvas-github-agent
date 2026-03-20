# Canvas Assignment Workflow

A deterministic workflow app that fetches assignments from Canvas, infers assignment type, and routes to the right destination:

- Coding assignment -> create a GitHub repository with starter files
- Writing assignment -> create a Notion page

The runtime architecture is orchestration-first, not a multi-agent task pipeline.

## Core Behavior

1. Fetch assignment from Canvas (specific assignment ID or next upcoming fallback)
2. Infer coding vs writing from assignment text (or accept explicit override)
3. Route to destination:
   - GitHub for coding assignments
   - Notion for writing assignments

## Architecture

- app/agent.py: workflow orchestrator and CLI command entrypoint
- app/cli.py: interactive CLI
- api.py: FastAPI surface for frontend and integrations
- tools/canvas_tools.py: Canvas integration wrapper (MCP first with direct REST fallback)
- tools/github_tools.py: GitHub integration wrapper
- tools/notion_tools.py: Notion integration wrapper
- scaffolding/templates.py: starter file generation

## Requirements

- Python 3.10+
- Node.js 20+ (for MCP tooling)
- Canvas API token
- GitHub token
- Notion token and parent page ID (for writing assignments)

## Installation

```bash
git clone https://github.com/willdaly/canvas-github-agent.git
cd canvas-github-agent
pip install -r requirements.txt
cp .env.example .env
```

Set values in .env:

- CANVAS_API_URL
- CANVAS_API_TOKEN
- CANVAS_USE_MCP
- GITHUB_TOKEN
- GITHUB_USERNAME
- GITHUB_ORG (optional)
- NOTION_TOKEN
- NOTION_PARENT_PAGE_ID
- FRONTEND_ORIGINS

Notes:

- CANVAS_USE_MCP=true uses the Smithery-hosted Canvas MCP server.
- CANVAS_USE_MCP=false uses direct Canvas REST calls and is recommended for headless server deployments.

## Usage

Interactive mode:

```bash
canvas-github-agent-cli
```

Command mode:

```bash
canvas-github-agent list-courses
canvas-github-agent list-assignments --course-id 12345
canvas-github-agent create-repo --course-id 12345
canvas-github-agent create-repo --course-id 12345 --assignment-id 67890
canvas-github-agent create-repo --course-id 12345 --language r
canvas-github-agent create-repo --course-id 12345 --assignment-type writing
canvas-github-agent create-repo --course-id 12345 --confirm-type
```

## API Endpoints

- GET /courses
- GET /courses/{course_id}/assignments
- POST /create

## Frontend

A Vite frontend is included under frontend/. See frontend/README.md.

## Future Enhancements

A richer assignment interpretation step (for more nuanced routing) can be added later as a small extension point in the orchestrator, without introducing a full multi-agent framework.

## License

MIT. See LICENSE.
