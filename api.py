"""
FastAPI server to expose CanvasGitHubAgent as a REST API for the frontend.
Place this file in the root of the canvas-github-agent project.
Install: pip install fastapi uvicorn
Run:     uvicorn api:app --reload
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from main import CanvasGitHubAgent, list_courses, list_course_assignments
from canvas_tools import CanvasTools

app = FastAPI(title="Canvas Assignment Agent API")

# Allow React frontend to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request body for /create ──────────────────────────────────────────────────
class CreateRequest(BaseModel):
    course_id: int
    assignment_id: Optional[int] = None
    language: str = "python"
    assignment_type: Optional[str] = None  # "coding" or "writing"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/courses")
async def get_courses():
    """Return all Canvas courses for the authenticated user."""
    try:
        canvas = CanvasTools()
        courses = await canvas.list_courses()
        return {"courses": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/courses/{course_id}/assignments")
async def get_assignments(course_id: int):
    """Return all assignments for a given course."""
    try:
        canvas = CanvasTools()
        assignments = await canvas.get_course_assignments(course_id)
        return {"assignments": assignments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        )
        if not result:
            raise HTTPException(status_code=400, detail="Agent failed to create destination.")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))