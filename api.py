"""FastAPI server exposing the Canvas assignment workflow orchestrator."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import CanvasGitHubAgent
from scaffolding.templates import build_service_oasf_record
from tools.canvas_tools import CanvasTools
from tools.course_context_tools import CourseContextTools


logger = logging.getLogger(__name__)

SERVICE_NAME = "Canvas Assignment Workflow"
SERVICE_SLUG = "canvas-assignment-workflow"
SERVICE_VERSION = "0.1.0"
MCP_SERVER_NAME = "canvas-assignment-workflow"
MCP_SERVER_COMMAND = "canvas-github-agent-mcp"
TASK_RESULT_SCHEMA = "task_result_v1"
TASK_STATUS_SCHEMA = "task_status_v1"
TASK_STORE: dict[str, dict[str, Any]] = {}


def get_allowed_origins() -> list[str]:
    """Resolve frontend origins from env, with local development defaults."""
    configured = os.getenv("FRONTEND_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def get_service_base_url() -> str:
    """Resolve the public base URL for this service."""
    configured = os.getenv("SERVICE_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return "http://localhost:8000"


def build_capabilities_payload() -> dict[str, Any]:
    """Describe the stable service contract for agent discovery and invocation."""
    base_url = get_service_base_url()
    return {
        "service": {
            "name": SERVICE_NAME,
            "slug": SERVICE_SLUG,
            "version": SERVICE_VERSION,
            "base_url": base_url,
        },
        "operations": [
            {
                "name": "list_courses",
                "method": "GET",
                "path": "/courses",
                "description": "List Canvas courses visible to the configured user.",
            },
            {
                "name": "list_assignments",
                "method": "GET",
                "path": "/courses/{course_id}/assignments",
                "description": "List assignments for a Canvas course.",
            },
            {
                "name": "list_course_modules",
                "method": "GET",
                "path": "/courses/{course_id}/modules",
                "description": "List Canvas modules and module items for a course.",
            },
            {
                "name": "search_course_modules",
                "method": "POST",
                "path": "/courses/{course_id}/modules/search",
                "description": "Search Canvas course module content for assignment-relevant context.",
            },
            {
                "name": "get_oasf_record",
                "method": "GET",
                "path": "/metadata/oasf-record",
                "description": "Return the service-level OASF record.",
            },
            {
                "name": "ingest_course_document",
                "method": "POST",
                "path": "/courses/{course_id}/documents/ingest",
                "description": "Parse a course PDF with Docling and index it into Chroma.",
            },
            {
                "name": "list_course_documents",
                "method": "GET",
                "path": "/courses/{course_id}/documents",
                "description": "List course documents already indexed for retrieval.",
            },
            {
                "name": "search_course_context",
                "method": "POST",
                "path": "/courses/{course_id}/context/search",
                "description": "Search indexed course documents for assignment-relevant context.",
            },
            {
                "name": "create_destination",
                "method": "POST",
                "path": "/create",
                "description": (
                    "Create a GitHub repository for coding assignments or a "
                    "Notion page for writing assignments."
                ),
            },
            {
                "name": "submit_task",
                "method": "POST",
                "path": "/tasks",
                "description": "Queue assignment provisioning work for asynchronous execution.",
            },
            {
                "name": "get_task_status",
                "method": "GET",
                "path": "/tasks/{task_id}",
                "description": "Fetch the current status and result of a submitted task.",
            },
        ],
        "authentication": {
            "service": "none",
            "upstream_dependencies": [
                "CANVAS_API_TOKEN",
                "GITHUB_TOKEN for coding assignment flow",
                "NOTION_TOKEN for writing assignment flow",
            ],
        },
        "transports": {
            "http": {
                "base_url": base_url,
                "health_path": "/health",
                "capabilities_path": "/capabilities",
            },
            "mcp_stdio": {
                "server_name": MCP_SERVER_NAME,
                "command": MCP_SERVER_COMMAND,
                "resources": [
                    "canvas-assignment-workflow://capabilities",
                    "canvas-assignment-workflow://metadata/oasf-record",
                ],
            },
        },
        "routing": {
            "assignment_types": ["coding", "writing"],
            "destinations": ["github", "notion"],
            "supported_languages": ["python", "r"],
            "course_context_backend": "chroma",
            "course_context_parser": "docling",
            "course_context_sources": ["canvas_modules", "chroma_documents"],
        },
        "result_schema": {
            "name": TASK_RESULT_SCHEMA,
            "top_level_fields": [
                "status",
                "service",
                "request",
                "route",
                "assignment",
                "artifacts",
                "details",
            ],
        },
        "task_schema": {
            "name": TASK_STATUS_SCHEMA,
            "top_level_fields": [
                "task_id",
                "status",
                "service",
                "request",
                "submitted_at",
                "started_at",
                "completed_at",
                "failed_at",
                "result",
                "error",
            ],
        },
    }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _summarize_assignment(assignment: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not assignment:
        return None

    return {
        "id": assignment.get("id"),
        "name": assignment.get("name"),
        "due_at": assignment.get("due_at"),
        "workflow_state": assignment.get("workflow_state"),
        "is_completed": assignment.get("is_completed"),
    }


def _request_payload(req: "CreateRequest") -> dict[str, Any]:
    return {
        "course_id": req.course_id,
        "assignment_id": req.assignment_id,
        "language": req.language,
        "assignment_type": req.assignment_type,
        "notion_content_mode": req.notion_content_mode,
    }


def _build_task_response(req: "CreateRequest", result: dict[str, Any]) -> dict[str, Any]:
    """Normalize workflow output into a stable task-result contract."""
    destination = result.get("destination")
    assignment_type = "coding" if destination == "github" else "writing"
    artifacts: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    repository = result.get("repository")
    if repository:
        artifacts.append(
            {
                "kind": "github_repository",
                "url": repository.get("html_url"),
                "owner": repository.get("owner", {}).get("login"),
                "name": repository.get("name"),
            }
        )
        details["files_created"] = result.get("files_created", [])
        details["files_uploaded"] = result.get("files_uploaded", False)

    page = result.get("page")
    if page:
        artifacts.append(
            {
                "kind": "notion_page",
                "url": page.get("url"),
                "id": page.get("id"),
            }
        )

    if result.get("course_context"):
        details["course_context"] = result["course_context"]

    return {
        "status": "completed",
        "service": {
            "name": SERVICE_NAME,
            "slug": SERVICE_SLUG,
            "version": SERVICE_VERSION,
        },
        "request": _request_payload(req),
        "route": {
            "assignment_type": assignment_type,
            "destination": destination,
            "language": req.language if assignment_type == "coding" else None,
            "notion_content_mode": (
                req.notion_content_mode or "structured"
                if assignment_type == "writing"
                else None
            ),
        },
        "assignment": _summarize_assignment(result.get("assignment")),
        "artifacts": artifacts,
        "details": details,
    }


def _build_task_status(
    *,
    task_id: str,
    request: dict[str, Any],
    status: str,
    submitted_at: str,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    failed_at: Optional[str] = None,
    result: Optional[dict[str, Any]] = None,
    error: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": status,
        "service": {
            "name": SERVICE_NAME,
            "slug": SERVICE_SLUG,
            "version": SERVICE_VERSION,
        },
        "request": request,
        "submitted_at": submitted_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "failed_at": failed_at,
        "result": result,
        "error": error,
    }


def _schedule_task_execution(task_id: str, req: "CreateRequest") -> None:
    asyncio.create_task(_execute_task(task_id, req))


async def _execute_task(task_id: str, req: "CreateRequest") -> None:
    task = TASK_STORE.get(task_id)
    if not task:
        return

    task["status"] = "running"
    task["started_at"] = _utcnow_iso()
    task["error"] = None

    try:
        agent = CanvasGitHubAgent()
        result = await agent.run(
            course_id=req.course_id,
            assignment_id=req.assignment_id,
            language=req.language,
            assignment_type=req.assignment_type,
            notion_content_mode=req.notion_content_mode,
        )

        if not result:
            task["status"] = "failed"
            task["failed_at"] = _utcnow_iso()
            task["error"] = {
                "code": "destination_creation_failed",
                "message": "Agent failed to create destination.",
            }
            return

        task["status"] = "completed"
        task["completed_at"] = _utcnow_iso()
        task["result"] = _build_task_response(req, result)
    except Exception:
        logger.exception("Failed to execute task_id=%s", task_id)
        task["status"] = "failed"
        task["failed_at"] = _utcnow_iso()
        task["error"] = {
            "code": "internal_execution_error",
            "message": "Task execution failed.",
        }


app = FastAPI(title="Canvas Assignment Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateRequest(BaseModel):
    course_id: int
    assignment_id: Optional[int] = None
    language: str = "python"
    assignment_type: Optional[str] = None
    notion_content_mode: Optional[str] = None


class CourseDocumentIngestRequest(BaseModel):
    file_path: str
    document_name: Optional[str] = None


class CourseContextSearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.get("/health")
async def get_health():
    """Return a minimal service health payload."""
    return {
        "status": "ok",
        "service": SERVICE_SLUG,
        "version": SERVICE_VERSION,
    }


@app.get("/capabilities")
async def get_capabilities():
    """Return a stable service capability description."""
    return build_capabilities_payload()


@app.post("/tasks", status_code=202)
async def submit_task(req: CreateRequest):
    """Queue assignment destination creation for asynchronous execution."""
    task_id = str(uuid4())
    TASK_STORE[task_id] = _build_task_status(
        task_id=task_id,
        request=_request_payload(req),
        status="queued",
        submitted_at=_utcnow_iso(),
    )
    _schedule_task_execution(task_id, req)
    return TASK_STORE[task_id]


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Return the status of a previously submitted task."""
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@app.get("/courses")
async def get_courses():
    """Return all Canvas courses for the authenticated user."""
    try:
        canvas = CanvasTools()
        courses = await canvas.list_courses()
        return {"courses": courses}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list Canvas courses")
        raise HTTPException(status_code=500, detail="Failed to fetch courses.")


@app.get("/courses/{course_id}/assignments")
async def get_assignments(course_id: int):
    """Return all assignments for a given course."""
    try:
        canvas = CanvasTools()
        assignments = await canvas.get_course_assignments(course_id)
        return {"assignments": assignments}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list assignments for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to fetch assignments.")


@app.get("/courses/{course_id}/modules")
async def get_modules(course_id: int):
    """Return Canvas modules for a given course."""
    try:
        canvas = CanvasTools()
        modules = await canvas.get_course_modules(course_id)
        return {"modules": modules}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list modules for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to fetch modules.")


@app.post("/courses/{course_id}/modules/search")
async def search_course_modules(course_id: int, req: CourseContextSearchRequest):
    """Search Canvas course modules for assignment-relevant context."""
    try:
        canvas = CanvasTools()
        results = await canvas.search_course_module_context(course_id, req.query, req.limit)
        return {
            "course_id": course_id,
            "query": req.query,
            "limit": req.limit,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to search modules for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to search course modules.")


@app.post("/courses/{course_id}/documents/ingest")
async def ingest_course_document(course_id: int, req: CourseDocumentIngestRequest):
    """Parse a local course PDF and index it into Chroma."""
    try:
        tools = CourseContextTools()
        return await asyncio.to_thread(tools.ingest_pdf, course_id, req.file_path, req.document_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Course document not found.")
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to ingest course document for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to ingest course document.")


@app.get("/courses/{course_id}/documents")
async def get_course_documents(course_id: int):
    """List course documents currently indexed for retrieval."""
    try:
        tools = CourseContextTools()
        documents = await asyncio.to_thread(tools.list_documents, course_id)
        return {"documents": documents}
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list course documents for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to list course documents.")


@app.post("/courses/{course_id}/context/search")
async def search_course_context(course_id: int, req: CourseContextSearchRequest):
    """Search the Chroma-backed course context store for a course."""
    try:
        tools = CourseContextTools()
        results = await asyncio.to_thread(tools.search_context, course_id, req.query, req.limit)
        return {
            "course_id": course_id,
            "query": req.query,
            "limit": req.limit,
            "results": results,
        }
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to search course context for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to search course context.")


@app.get("/metadata/oasf-record")
async def get_oasf_record():
    """Return the service-level OASF record for this workflow app."""
    try:
        return build_service_oasf_record(service_base_url=get_service_base_url())
    except Exception:
        logger.exception("Failed to build OASF service record")
        raise HTTPException(status_code=500, detail="Failed to build OASF record.")


@app.post("/create")
async def create_destination(req: CreateRequest):
    """Synchronously create the destination for a Canvas assignment."""
    try:
        agent = CanvasGitHubAgent()
        result = await agent.run(
            course_id=req.course_id,
            assignment_id=req.assignment_id,
            language=req.language,
            assignment_type=req.assignment_type,
            notion_content_mode=req.notion_content_mode,
        )
        if not result:
            raise HTTPException(status_code=400, detail="Agent failed to create destination.")
        return _build_task_response(req, result)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to create destination for course_id=%s assignment_id=%s",
            req.course_id,
            req.assignment_id,
        )
        raise HTTPException(status_code=500, detail="Failed to create destination.")