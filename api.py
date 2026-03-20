"""FastAPI server exposing the Canvas assignment workflow orchestrator."""
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.agent import CanvasGitHubAgent
from tools.canvas_tools import CanvasTools


logger = logging.getLogger(__name__)


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
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to create destination for course_id=%s assignment_id=%s",
            req.course_id,
            req.assignment_id,
        )
        raise HTTPException(status_code=500, detail="Failed to create destination.")