"""FastAPI server exposing the Canvas assignment workflow orchestrator."""
import logging
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agent import CanvasGitHubAgent
from scaffolding.templates import build_service_oasf_record
from tools.canvas_tools import CanvasTools


logger = logging.getLogger(__name__)

SERVICE_NAME = "Canvas Assignment Workflow"
SERVICE_SLUG = "canvas-assignment-workflow"
SERVICE_VERSION = "0.1.0"


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
                "name": "get_oasf_record",
                "method": "GET",
                "path": "/metadata/oasf-record",
                "description": "Return the service-level OASF record.",
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
        ],
        "authentication": {
            "service": "none",
            "upstream_dependencies": [
                "CANVAS_API_TOKEN",
                "GITHUB_TOKEN for coding assignment flow",
                "NOTION_TOKEN for writing assignment flow",
            ],
        },
        "routing": {
            "assignment_types": ["coding", "writing"],
            "destinations": ["github", "notion"],
            "supported_languages": ["python", "r"],
        },
        "result_schema": {
            "name": "task_result_v1",
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
    }


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

    return {
        "status": "completed",
        "service": {
            "name": SERVICE_NAME,
            "slug": SERVICE_SLUG,
            "version": SERVICE_VERSION,
        },
        "request": {
            "course_id": req.course_id,
            "assignment_id": req.assignment_id,
            "language": req.language,
            "assignment_type": req.assignment_type,
            "notion_content_mode": req.notion_content_mode,
        },
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


app = FastAPI(title="Canvas Assignment Agent API")

# Allow React frontend to talk to this server
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
    assignment_type: Optional[str] = None  # "coding" or "writing"
    notion_content_mode: Optional[str] = None  # "structured" or "text"


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
    """
    Create a GitHub repo (coding) or Notion page (writing) for an assignment.
    The agent auto-detects coding vs writing if assignment_type is not provided.
    """
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