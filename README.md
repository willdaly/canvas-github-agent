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

[View interactive system architecture diagram on Miro](https://miro.com/app/board/uXjVGl7o1Oo=/?moveToWidget=3458764666993741044)

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

- **Multi-user web UI:** set `CREDENTIAL_ENCRYPTION_KEY` to a Fernet key (see `.env.example`). Users paste Northeastern Canvas and GitHub tokens in the UI; tokens are encrypted at rest in SQLite (`.data/users.sqlite3` by default). The MCP server and CLI continue to use `CANVAS_API_TOKEN` / `GITHUB_TOKEN` from the environment. Writing assignments still use server `NOTION_TOKEN` / `NOTION_PARENT_PAGE_ID` unless you extend the model.
- `CANVAS_INSTITUTION_URL` defaults to Northeastern Canvas; the UI does not ask for an institution URL.
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
- POST /discover-agents
- POST /plan
- POST /create
- POST /tasks
- GET /tasks/{task_id}
- GET /tasks/{task_id}/steps
- GET /tasks/{task_id}/artifacts
- POST /tasks/{task_id}/resume
- POST /tasks/{task_id}/inspect-delegation-tool
- GET /agents/scorecards

The `/discover-agents` endpoint returns an `agent_candidate_v1`-style payload with ranked delegation candidates. By default it returns seeded AGNTCY-ecosystem candidates and can optionally include live Smithery-backed MCP search results.

The `/plan` endpoint returns a stable `assignment_plan_v1` payload with assignment, plan, recommendations, and confidence fields so callers can inspect the execution strategy before creating artifacts.

The `/create` endpoint returns a stable `task_result_v1` payload with service, request, route, assignment, artifacts, and details fields.

When `enable_delegated_evaluation=true` is supplied to `/create` or `/tasks`, the workflow will attempt a Smithery-backed remote evaluation step after local artifact generation and attach both the delegated evaluation result and artifact provenance into `details`.

When `enable_delegated_execution=true` is supplied to `/create` or `/tasks`, the workflow will attempt a Smithery-backed remote execution step after local artifact generation and attach the delegated execution result into `details` before provenance is finalized.

The `/tasks` endpoints expose an asynchronous `task_status_v1` lifecycle with `queued`, `running`, `completed`, and `failed` states.

The `/tasks/{task_id}/steps` endpoint returns persisted `execution_step_v1` records for the task, and `/tasks/{task_id}/artifacts` returns the final artifact list plus provenance.

Task-step records now include retry metadata so repeated delegated or local step attempts expose `attempt_count`, `retry_count`, `last_retry_at`, and `retry_history` explicitly.

The `GET /tasks/{task_id}/steps` endpoint also supports `status`, `retried_only`, and `delegated_only` query filters so callers can focus on failed, retried, or delegated steps.

The `/tasks/{task_id}/resume` endpoint requeues a task and can retry only selected blocked or failed steps when local artifact generation has already succeeded.

The `/tasks/{task_id}/inspect-delegation-tool` endpoint resolves the schema-compatible remote tool that would be used for delegated execution or evaluation on the current task state, without actually invoking the remote tool.

Completed delegated step records now persist the executed `tool_selection` metadata in their step summaries so inspection output can be compared with the tool that actually ran.

The `/agents/scorecards` endpoint returns persisted `agent_scorecard_v1` summaries for remote execution and evaluation agents. Discovery responses now include scorecard context when historical delegation data exists.

Outbound delegation is gated by a simple allowlist policy. By default, explicit request targets are allowed, while discovery-only delegation is blocked unless one of these env vars matches the resolved target:

- `DELEGATION_ALLOWED_AGENT_IDS`
- `DELEGATION_ALLOWED_CONNECTION_IDS`
- `DELEGATION_ALLOWED_CONNECTION_URLS`

You can relax or tighten this behavior with:

- `DELEGATION_REQUIRE_ALLOWLIST`
- `DELEGATION_ALLOW_EXPLICIT_REQUESTS`
- `REMOTE_EVALUATION_ENABLED`
- `REMOTE_EXECUTION_ENABLED`

Course PDFs can be ingested with Docling and indexed into a local Chroma store. During assignment creation, the app will search both indexed course documents and live Canvas module content, then attach the most relevant excerpts to generated outputs.

For explicit maze-search assignments that require `maze_solvers.py`, the generator now emits a working Python maze project with BFS, DFS, A* implementations, a benchmark script, a sample maze file, generated tests, and downloaded linked maze artifacts when the assignment brief exposes maze text files.

For ML project briefs, the generator now produces a project-oriented Python scaffold with a tailored report template, a presentation outline, NSL-KDD plus `kagglehub` starter code, EDA helpers, baseline model-training scripts, and validation tests instead of only the generic `main.py` placeholder.

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
- `discover_agents`
- `plan_assignment`
- `create_destination`
- `submit_task`
- `get_task_status`
- `resume_task`
- `inspect_task_delegation_tool`
- `list_agent_scorecards`
- `list_task_steps`
- `list_task_artifacts`

Static MCP resources:

- `canvas-assignment-workflow://capabilities`
- `canvas-assignment-workflow://metadata/oasf-record`
- `canvas-assignment-workflow://schemas/execution-step-v1`
- `canvas-assignment-workflow://schemas/agent-scorecard-v1`
- `canvas-assignment-workflow://schemas/resume-task-v1`
- `canvas-assignment-workflow://schemas/delegation-tool-inspection-v1`
- `canvas-assignment-workflow://profiles/smithery-execution-pilot`

Local smoke test:

```bash
.venv/bin/python -m pytest tests/test_mcp_server.py -q
```

Claude Desktop config template:

- `examples/claude_desktop_config.template.json`
- `examples/smithery_execution_profile.template.json`

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

The concrete roadmap for evolving this app into an AGNTCY-oriented coordinator, including discovery, delegation, provenance, and candidate external agent categories, is documented in `docs/agntcy-ioa-roadmap.md`.

## License

MIT. See LICENSE.
