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
- app/mcp_server.py: FastMCP stdio server for agent-tool interoperability
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
- Docling and Chroma dependencies for course-context retrieval

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
- SERVICE_BASE_URL (optional; defaults to `http://localhost:8000`)
- COURSE_CONTEXT_CHROMA_PATH (optional; defaults to `.chroma`)
- COURSE_CONTEXT_COLLECTION (optional; defaults to `course-context`)
- COURSE_CONTEXT_DEFAULT_LIMIT (optional; defaults to `5`)
- CANVAS_MODULE_CACHE_TTL_SECONDS (optional; defaults to `300`)

Notes:

- CANVAS_USE_MCP=true uses the Smithery-hosted Canvas MCP server.
- CANVAS_USE_MCP=false uses direct Canvas REST calls and is recommended for headless server deployments.
- CANVAS_MODULE_CACHE_TTL_SECONDS controls lightweight in-process caching for Canvas module lookups to reduce repeated API requests.
- When Canvas responses include `updated_at`-style metadata, cached module-item content is versioned by that revision data so content refreshes can bypass the TTL cache earlier.

## Usage

Interactive mode:

```bash
canvas-github-agent-cli
```

Command mode:

```bash
canvas-github-agent list-courses
canvas-github-agent list-assignments --course-id 12345
canvas-github-agent list-modules --course-id 12345
canvas-github-agent create-repo --course-id 12345
canvas-github-agent create-repo --course-id 12345 --assignment-id 67890
canvas-github-agent create-repo --course-id 12345 --language r
canvas-github-agent create-repo --course-id 12345 --assignment-type writing
canvas-github-agent create-repo --course-id 12345 --confirm-type
canvas-github-agent ingest-pdf --course-id 12345 --file-path "docs/AAI6660_Spring_2026 (1).pdf"
canvas-github-agent list-documents --course-id 12345
canvas-github-agent search-context --course-id 12345 --query "Bayes theorem posterior update"
canvas-github-agent search-modules --course-id 12345 --query "Bayes theorem posterior update"
```

## API Endpoints

- GET /health
- GET /capabilities
- GET /courses
- GET /courses/{course_id}/assignments
- GET /courses/{course_id}/modules
- POST /courses/{course_id}/modules/search
- POST /courses/{course_id}/documents/ingest
- GET /courses/{course_id}/documents
- POST /courses/{course_id}/context/search
- GET /metadata/oasf-record
- POST /create
- POST /tasks
- GET /tasks/{task_id}

The `/create` endpoint returns a stable `task_result_v1` payload with service, request, route, assignment, artifacts, and details fields.

The `/tasks` endpoints expose an asynchronous `task_status_v1` lifecycle with `queued`, `running`, `completed`, and `failed` states.

Course PDFs can be ingested with Docling and indexed into a local Chroma store. During assignment creation, the app will search both indexed course documents and live Canvas module content, then attach the most relevant excerpts to generated outputs.

For explicit maze-search assignments that require `maze_solvers.py`, the generator now emits a working Python maze project with BFS, DFS, A* implementations, a benchmark script, a sample maze file, generated tests, and downloaded linked maze artifacts when the assignment brief exposes maze text files.

## MCP Server

The project also exposes an MCP stdio server so other agents and MCP-compatible clients can invoke the workflow directly.

Run it with:

```bash
canvas-github-agent-mcp
```

Primary MCP tools:

- `list_courses`
- `list_assignments`
- `list_course_modules`
- `search_course_modules`
- `get_capabilities`
- `get_oasf_record`
- `ingest_course_document`
- `list_course_documents`
- `search_course_context`
- `create_destination`
- `submit_task`
- `get_task_status`

Static MCP resources:

- `canvas-assignment-workflow://capabilities`
- `canvas-assignment-workflow://metadata/oasf-record`

Local smoke test:

```bash
.venv/bin/python -m pytest tests/test_mcp_server.py -q
```

Claude Desktop config template:

- `examples/claude_desktop_config.template.json`

Claude Desktop expects absolute paths. Update the template paths and env values, then add the entry under `~/Library/Application Support/Claude/claude_desktop_config.json` and fully restart Claude Desktop.

## Course Context

The repository now supports two deterministic course-context sources:

- live Canvas module content retrieved through the Canvas API
- a local Chroma-backed retrieval store for reference material such as slide decks

- Read module pages, assignments, and discussion topics from Canvas and rank the most relevant excerpts against the assignment text
- Use Docling to parse PDFs into markdown-like text chunks
- Store those chunks in Chroma with course-scoped metadata
- Retrieve relevant excerpts during assignment creation so generated repos and pages can reference both Canvas modules and uploaded course materials

Local Chroma data is stored under `.chroma/` by default and is ignored by git.

## Frontend

A Vite frontend is included under frontend/. See frontend/README.md.

## Agent Fact Card

The required service fact card is stored at metadata/agent-fact-cards/service.canvas-assignment-workflow.fact-card.json.

A minimal OASF 1.0.0-compatible service record is also stored at metadata/oasf-records/service.canvas-assignment-workflow.record.json.

## Future Enhancements

A richer assignment interpretation step (for more nuanced routing) can be added later as a small extension point in the orchestrator, without introducing a full multi-agent framework.

## License

MIT. See LICENSE.
