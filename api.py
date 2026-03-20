"""FastAPI server exposing the Canvas assignment workflow orchestrator."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import CanvasGitHubAgent
from app.auth_context import (
    USER_STORE,
    optional_session_user_id,
    session_auth_enabled,
    workflow_credentials_for_env,
    workflow_credentials_for_http,
)
from app.credentials import WorkflowCredentials, get_canvas_institution_url
from app.delegation_policy import evaluate_delegation_policy
from app.planning import generate_assignment_plan
from app.provenance import build_artifact_provenance
from app.registry import AgentRegistry
from app.remote_agents import (
    SmitheryRemoteAgentClient,
    delegated_evaluation_enabled_by_default,
    delegated_execution_enabled_by_default,
)
from app.task_store import SQLiteTaskStore
from scaffolding.templates import build_service_oasf_record
from tools.canvas_tools import CanvasTools
from tools.course_context_tools import CourseContextTools
from app.user_store import SESSION_COOKIE_NAME, SESSION_TTL_DAYS


logger = logging.getLogger(__name__)

SERVICE_NAME = "Canvas Assignment Workflow"
SERVICE_SLUG = "canvas-assignment-workflow"
SERVICE_VERSION = "0.1.0"
MCP_SERVER_NAME = "canvas-assignment-workflow"
MCP_SERVER_COMMAND = "canvas-github-agent-mcp"
DISCOVERY_SCHEMA = "agent_candidate_v1"
PLAN_SCHEMA = "assignment_plan_v1"
TASK_RESULT_SCHEMA = "task_result_v1"
TASK_STATUS_SCHEMA = "task_status_v1"
TASK_STEP_SCHEMA = "execution_step_v1"
SCORECARD_SCHEMA = "agent_scorecard_v1"
TASK_STORE = SQLiteTaskStore()
AGENT_REGISTRY = AgentRegistry()
REMOTE_AGENT_CLIENT = SmitheryRemoteAgentClient()


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
                "name": "discover_agents",
                "method": "POST",
                "path": "/discover-agents",
                "description": "Return ranked external agent candidates for a requested capability family or search query.",
            },
            {
                "name": "plan_assignment",
                "method": "POST",
                "path": "/plan",
                "description": "Analyze an assignment and return a structured execution plan without publishing artifacts.",
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
            {
                "name": "list_task_steps",
                "method": "GET",
                "path": "/tasks/{task_id}/steps",
                "description": "List the persisted execution_step_v1 records for a task.",
            },
            {
                "name": "list_task_artifacts",
                "method": "GET",
                "path": "/tasks/{task_id}/artifacts",
                "description": "List generated artifacts and provenance for a task.",
            },
            {
                "name": "resume_task",
                "method": "POST",
                "path": "/tasks/{task_id}/resume",
                "description": "Resume a failed or partially completed task, optionally retrying selected steps only.",
            },
            {
                "name": "inspect_task_delegation_tool",
                "method": "POST",
                "path": "/tasks/{task_id}/inspect-delegation-tool",
                "description": "Resolve the schema-compatible remote tool that would be used for a delegated execution or evaluation step.",
            },
            {
                "name": "list_agent_scorecards",
                "method": "GET",
                "path": "/agents/scorecards",
                "description": "List persisted agent delegation scorecards used for ranking feedback.",
            },
        ],
        "authentication": {
            "service": "session_cookie_optional",
            "description": (
                "When CREDENTIAL_ENCRYPTION_KEY is set, the web UI uses POST /auth/session "
                "with per-user Canvas and GitHub tokens (httpOnly cookie). "
                "Otherwise the API uses CANVAS_API_TOKEN and GITHUB_TOKEN from the environment. "
                "MCP tools always use environment credentials."
            ),
            "upstream_dependencies": [
                "CANVAS_API_TOKEN or browser session token",
                "GITHUB_TOKEN or browser session token for coding flow",
                "NOTION_TOKEN for writing flow (server env)",
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
                    "canvas-assignment-workflow://schemas/execution-step-v1",
                    "canvas-assignment-workflow://schemas/agent-scorecard-v1",
                    "canvas-assignment-workflow://schemas/resume-task-v1",
                    "canvas-assignment-workflow://schemas/delegation-tool-inspection-v1",
                    "canvas-assignment-workflow://profiles/smithery-execution-pilot",
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
        "discovery_schema": {
            "name": DISCOVERY_SCHEMA,
            "top_level_fields": [
                "status",
                "service",
                "query",
                "candidates",
            ],
        },
        "planning_schema": {
            "name": PLAN_SCHEMA,
            "top_level_fields": [
                "status",
                "service",
                "request",
                "assignment",
                "plan",
                "recommendations",
                "confidence",
            ],
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
        "task_step_schema": {
            "name": TASK_STEP_SCHEMA,
            "top_level_fields": [
                "task_id",
                "step_id",
                "title",
                "position",
                "mode",
                "capability_family",
                "status",
                "started_at",
                "completed_at",
                "failed_at",
                "agent",
                "policy",
                "summary",
                "result",
                "error",
            ],
        },
        "scorecard_schema": {
            "name": SCORECARD_SCHEMA,
            "top_level_fields": [
                "agent_id",
                "capability_family",
                "success_count",
                "failure_count",
                "blocked_count",
                "total_count",
                "success_rate",
                "last_status",
                "last_tool_name",
                "updated_at",
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
        "enable_delegated_evaluation": req.enable_delegated_evaluation,
        "evaluation_agent_id": req.evaluation_agent_id,
        "evaluation_connection_id": req.evaluation_connection_id,
        "evaluation_connection_url": req.evaluation_connection_url,
        "evaluation_tool_name": req.evaluation_tool_name,
        "evaluation_include_live_results": req.evaluation_include_live_results,
        "enable_delegated_execution": req.enable_delegated_execution,
        "execution_agent_id": req.execution_agent_id,
        "execution_connection_id": req.execution_connection_id,
        "execution_connection_url": req.execution_connection_url,
        "execution_tool_name": req.execution_tool_name,
        "execution_include_live_results": req.execution_include_live_results,
    }


def _canvas_tools_from_credentials(creds: WorkflowCredentials) -> CanvasTools:
    use_mcp = False if session_auth_enabled() else None
    return CanvasTools(canvas_url=creds.canvas_url, canvas_token=creds.canvas_token, use_mcp=use_mcp)


def _assert_task_visible(task: dict[str, Any], request: Optional[Request]) -> None:
    if not session_auth_enabled() or request is None:
        return
    uid = optional_session_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    owner = task.get("owner_user_id")
    if owner is not None and int(owner) != int(uid):
        raise HTTPException(status_code=404, detail="Task not found.")


def _credentials_for_task_owner(owner_user_id: Optional[int]) -> Optional[WorkflowCredentials]:
    if owner_user_id is None:
        return None
    canvas_tok, github_tok, github_user = USER_STORE.decrypt_workflow_tokens(int(owner_user_id))
    _org = os.getenv("GITHUB_ORG", "").strip()
    github_org = _org if _org and not _org.startswith("#") else ""
    return WorkflowCredentials(
        canvas_url=get_canvas_institution_url(),
        canvas_token=canvas_tok,
        github_token=github_tok,
        github_username=github_user,
        github_org=github_org,
    ).with_notion_from_env()


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
    owner_user_id: Optional[int] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
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
    if owner_user_id is not None:
        payload["owner_user_id"] = owner_user_id
    return payload


def _build_plan_response(req: "CreateRequest", plan_result: dict[str, Any]) -> dict[str, Any]:
    """Normalize planning output into a stable pre-execution contract."""
    return {
        "status": "planned",
        "service": {
            "name": SERVICE_NAME,
            "slug": SERVICE_SLUG,
            "version": SERVICE_VERSION,
        },
        "request": _request_payload(req),
        "assignment": plan_result["assignment"],
        "plan": plan_result["plan"],
        "recommendations": plan_result["recommendations"],
        "confidence": plan_result["confidence"],
    }


def _build_discovery_response(req: "DiscoverAgentsRequest", candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize discovery output into a stable response contract."""
    return {
        "status": "ok",
        "service": {
            "name": SERVICE_NAME,
            "slug": SERVICE_SLUG,
            "version": SERVICE_VERSION,
        },
        "query": {
            "capability_family": req.capability_family,
            "query": req.query,
            "limit": req.limit,
            "include_live_results": req.include_live_results,
            "verified_only": req.verified_only,
        },
        "candidates": candidates,
    }
    # Adding execution step schema
def build_execution_step_schema() -> dict[str, Any]:
    """Return a machine-readable schema description for execution_step_v1."""
    return {
        "name": TASK_STEP_SCHEMA,
        "type": "object",
        "required": ["task_id", "step_id", "title", "position", "mode", "status"],
        "properties": {
            "task_id": {"type": "string"},
            "step_id": {"type": "string"},
            "title": {"type": "string"},
            "position": {"type": "integer"},
            "mode": {"type": "string"},
            "capability_family": {"type": ["string", "null"]},
            "status": {"type": "string"},
            "started_at": {"type": ["string", "null"]},
            "completed_at": {"type": ["string", "null"]},
            "failed_at": {"type": ["string", "null"]},
            "attempt_count": {"type": "integer"},
            "retry_count": {"type": "integer"},
            "last_retry_at": {"type": ["string", "null"]},
            "retry_history": {"type": "array", "items": {"type": "object"}},
            "agent": {"type": ["object", "null"]},
            "policy": {"type": ["object", "null"]},
            "summary": {"type": ["object", "null"]},
            "result": {"type": ["object", "null"]},
            "error": {"type": ["object", "null"]},
        },
    }

def build_agent_scorecard_schema() -> dict[str, Any]:
    """Return a machine-readable schema description for agent_scorecard_v1."""
    return {
        "name": SCORECARD_SCHEMA,
        "type": "object",
        "required": ["agent_id", "capability_family", "success_count", "failure_count", "blocked_count", "total_count", "success_rate"],
        "properties": {
            "agent_id": {"type": "string"},
            "capability_family": {"type": "string"},
            "success_count": {"type": "integer"},
            "failure_count": {"type": "integer"},
            "blocked_count": {"type": "integer"},
            "total_count": {"type": "integer"},
            "success_rate": {"type": "number"},
            "last_status": {"type": ["string", "null"]},
            "last_tool_name": {"type": ["string", "null"]},
            "last_task_id": {"type": ["string", "null"]},
            "last_step_id": {"type": ["string", "null"]},
            "updated_at": {"type": ["string", "null"]},
        },
    }

def build_resume_task_schema() -> dict[str, Any]:
    """Return a machine-readable schema description for task resume requests."""
    return {
        "name": "resume_task_v1",
        "type": "object",
        "required": [],
        "properties": {
            "step_ids": {"type": ["array", "null"], "items": {"type": "string"}},
            "force_full_rerun": {"type": "boolean"},
        },
    }


def build_delegation_tool_inspection_schema() -> dict[str, Any]:
    """Return a machine-readable schema description for delegation tool inspection responses."""
    return {
        "name": "delegation_tool_inspection_v1",
        "type": "object",
        "required": ["status", "task_id", "capability_family", "candidate", "policy", "requested_tool_name"],
        "properties": {
            "status": {"type": "string"},
            "task_id": {"type": "string"},
            "capability_family": {"type": "string"},
            "candidate": {"type": "object"},
            "policy": {"type": "object"},
            "requested_tool_name": {"type": "string"},
            "tool_selection": {
                "type": ["object", "null"],
                "properties": {
                    "tool_name": {"type": "string"},
                    "schema": {"type": "object"},
                    "connection_id": {"type": ["string", "null"]},
                    "connection_url": {"type": ["string", "null"]},
                },
            },
        },
    }


def _create_request_from_payload(payload: dict[str, Any]) -> "CreateRequest":
    """Rehydrate a validated CreateRequest from persisted task request payloads."""
    return CreateRequest(**payload)


def _scorecard_bonus(scorecard: dict[str, Any]) -> float:
    total_count = int(scorecard.get("total_count") or 0)
    if total_count == 0:
        return 0.0
    success_rate = float(scorecard.get("success_rate") or 0.0)
    confidence = min(total_count / 10.0, 1.0)
    return round((success_rate - 0.5) * 0.2 * confidence, 3)


def _attach_scorecards_to_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_copy = dict(candidate)
        ranking = dict(candidate_copy.get("ranking", {}))
        original_score = float(ranking.get("score", 0.0) or 0.0)
        agent_id = candidate_copy.get("agent_id")
        capability_family = candidate_copy.get("capability_family")
        explanation = {
            "base_score": round(original_score, 3),
            "final_score": round(original_score, 3),
            "scorecard_bonus": 0.0,
            "scorecard_applied": False,
            "summary": "Ranked using capability fit and source signals only.",
        }
        if agent_id and capability_family:
            scorecard = TASK_STORE.get_agent_scorecard(agent_id, capability_family)
            if scorecard:
                candidate_copy["scorecard"] = scorecard
                bonus = _scorecard_bonus(scorecard)
                ranking["scorecard_bonus"] = bonus
                if "score" in ranking:
                    ranking["score"] = round(float(ranking["score"]) + bonus, 3)
                candidate_copy["ranking"] = ranking
                explanation = {
                    "base_score": round(original_score, 3),
                    "final_score": round(float(ranking.get("score", original_score)), 3),
                    "scorecard_bonus": bonus,
                    "scorecard_applied": True,
                    "summary": (
                        f"Applied scorecard bonus of {bonus:+.3f} from success_rate="
                        f"{float(scorecard.get('success_rate') or 0.0):.3f} over "
                        f"{int(scorecard.get('total_count') or 0)} observed delegations."
                    ),
                }
        candidate_copy["ranking_explanation"] = explanation
        enriched.append(candidate_copy)

    enriched.sort(key=lambda item: item.get("ranking", {}).get("score", 0), reverse=True)
    return enriched


def _refresh_artifact_provenance(task_response: dict[str, Any]) -> dict[str, Any]:
    task_response.setdefault("details", {})["artifact_provenance"] = build_artifact_provenance(
        task_response,
        delegated_execution=task_response.get("details", {}).get("delegated_execution"),
        delegated_evaluation=task_response.get("details", {}).get("delegated_evaluation"),
    )
    return task_response


def _record_agent_scorecard_event(task_id: Optional[str], result: dict[str, Any], capability_family: str) -> None:
    agent = result.get("agent") or {}
    agent_id = agent.get("agent_id")
    if not agent_id:
        return

    TASK_STORE.record_agent_scorecard_event(
        agent_id=agent_id,
        capability_family=capability_family,
        status=result.get("status", "failed"),
        tool_name=result.get("request_summary", {}).get("tool_name"),
        task_id=task_id,
        step_id=result.get("subtask_id"),
    )


def _build_task_step(
    *,
    task_id: str,
    step_id: str,
    title: str,
    position: int,
    mode: str,
    status: str,
    capability_family: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    failed_at: Optional[str] = None,
    attempt_count: int = 1,
    retry_count: int = 0,
    last_retry_at: Optional[str] = None,
    retry_history: Optional[list[dict[str, Any]]] = None,
    agent: Optional[dict[str, Any]] = None,
    policy: Optional[dict[str, Any]] = None,
    summary: Optional[dict[str, Any]] = None,
    result: Optional[dict[str, Any]] = None,
    error: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "title": title,
        "position": position,
        "mode": mode,
        "capability_family": capability_family,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "failed_at": failed_at,
        "attempt_count": attempt_count,
        "retry_count": retry_count,
        "last_retry_at": last_retry_at,
        "retry_history": retry_history or [],
        "agent": agent,
        "policy": policy,
        "summary": summary,
        "result": result,
        "error": error,
    }


def _step_history_entry(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": step.get("status"),
        "started_at": step.get("started_at"),
        "completed_at": step.get("completed_at"),
        "failed_at": step.get("failed_at"),
        "summary": step.get("summary"),
        "error": step.get("error"),
    }


def _merge_step_retry_metadata(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    existing = TASK_STORE.get_step(task_id, str(step.get("step_id") or ""))
    if not existing:
        step.setdefault("attempt_count", 1)
        step.setdefault("retry_count", 0)
        step.setdefault("last_retry_at", None)
        step.setdefault("retry_history", [])
        return step

    attempt_count = int(existing.get("attempt_count") or 1)
    retry_history = list(existing.get("retry_history") or [])
    last_retry_at = existing.get("last_retry_at")

    if step.get("status") == "running" and existing.get("status") != "running":
        retry_history.append(_step_history_entry(existing))
        attempt_count += 1
        last_retry_at = step.get("started_at") or _utcnow_iso()

    step["attempt_count"] = max(int(step.get("attempt_count") or 0), attempt_count)
    step["retry_count"] = max(step["attempt_count"] - 1, 0)
    step["last_retry_at"] = step.get("last_retry_at") or last_retry_at
    step["retry_history"] = retry_history
    return step


def _save_task_step(task_id: str, step: dict[str, Any]) -> None:
    TASK_STORE.save_step(task_id, _merge_step_retry_metadata(task_id, dict(step)))


def _delegation_intent_queries(capability_family: str, requested_tool_name: str) -> list[str]:
    queries = [requested_tool_name]
    if capability_family == "execution":
        queries.extend(["execute assignment", "run tests", "execute project", "run benchmark"])
    else:
        queries.extend(["evaluate assignment", "validate project", "score assignment"])
    return list(dict.fromkeys(query for query in queries if query))


async def _inspect_task_delegation_tool(
    task_id: str,
    req: "CreateRequest",
    capability_family: str,
) -> dict[str, Any]:
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    task_response = task.get("result") or {}
    if not task_response:
        raise HTTPException(status_code=409, detail="Task does not have generated artifacts to inspect yet.")

    payload = _build_evaluation_payload(task_response)
    if capability_family == "execution":
        candidate = _resolve_execution_candidate(req)
        scorecard = TASK_STORE.get_agent_scorecard(candidate.get("agent_id", ""), "execution") if candidate.get("agent_id") else None
        explicit_request = any([req.execution_agent_id, req.execution_connection_id, req.execution_connection_url])
        requested_tool_name = req.execution_tool_name
        connection_id = req.execution_connection_id
        connection_url = req.execution_connection_url
    elif capability_family == "evaluation":
        candidate = _resolve_evaluation_candidate(req)
        scorecard = TASK_STORE.get_agent_scorecard(candidate.get("agent_id", ""), "evaluation") if candidate.get("agent_id") else None
        explicit_request = any([req.evaluation_agent_id, req.evaluation_connection_id, req.evaluation_connection_url])
        requested_tool_name = req.evaluation_tool_name
        connection_id = req.evaluation_connection_id
        connection_url = req.evaluation_connection_url
    else:
        raise HTTPException(status_code=400, detail="capability_family must be 'execution' or 'evaluation'.")

    policy = evaluate_delegation_policy(
        capability_family=capability_family,
        candidate=candidate,
        connection_id=connection_id,
        connection_url=connection_url,
        explicit_request=explicit_request,
        scorecard=scorecard,
    )
    if not policy["allowed"]:
        return {
            "status": "blocked",
            "task_id": task_id,
            "capability_family": capability_family,
            "candidate": candidate,
            "policy": policy,
            "requested_tool_name": requested_tool_name,
            "tool_selection": None,
        }

    resolved_connection_id = connection_id or REMOTE_AGENT_CLIENT._connection_id_from_name(
        candidate.get("agent_id") or candidate.get("name") or f"{capability_family}-agent"
    )
    resolved_connection_url = connection_url or candidate.get("invocation", {}).get("connection_url")
    inspection = await REMOTE_AGENT_CLIENT.inspect_assignment_tool(
        connection_id=resolved_connection_id,
        connection_url=resolved_connection_url,
        requested_tool_name=requested_tool_name,
        payload=payload,
        intent_queries=_delegation_intent_queries(capability_family, requested_tool_name),
    )
    return {
        "status": "ready",
        "task_id": task_id,
        "capability_family": capability_family,
        "candidate": candidate,
        "policy": policy,
        "requested_tool_name": requested_tool_name,
        "tool_selection": inspection,
    }


def _resolve_delegation_candidate(
    *,
    capability_family: str,
    requested_agent_id: Optional[str],
    connection_id: Optional[str],
    connection_url: Optional[str],
    include_live_results: bool,
    default_name: str,
) -> dict[str, Any]:
    if requested_agent_id:
        candidates = AGENT_REGISTRY.discover_agents(
            capability_family=capability_family,
            query=requested_agent_id,
            limit=10,
            include_live_results=include_live_results,
            verified_only=False,
        )
        for candidate in candidates:
            agent_id = candidate.get("agent_id", "")
            name = candidate.get("name", "")
            requested = requested_agent_id.lower()
            if requested == agent_id.lower() or requested == name.lower():
                return candidate
        if candidates:
            return candidates[0]

    if connection_id or connection_url:
        fallback_name = requested_agent_id or connection_id or default_name
        return {
            "agent_id": requested_agent_id or connection_id or f"custom-{capability_family}-agent",
            "name": fallback_name,
            "source": "explicit_request",
            "capability_family": capability_family,
            "capabilities": [capability_family],
            "protocols": ["mcp"],
            "trust_level": "explicit_request",
            "description": f"Explicit delegated {capability_family} target from the request payload.",
            "invocation": {
                "verified": False,
                "connection_url": connection_url,
            },
        }

    candidates = AGENT_REGISTRY.discover_agents(
        capability_family=capability_family,
        limit=1,
        include_live_results=include_live_results,
        verified_only=False,
    )
    if candidates:
        return candidates[0]

    return {
        "agent_id": f"unresolved-{capability_family}-agent",
        "name": default_name,
        "source": "fallback",
        "capability_family": capability_family,
        "capabilities": [capability_family],
        "protocols": ["mcp"],
        "trust_level": "unknown",
        "description": f"Fallback placeholder when no {capability_family} candidate could be resolved.",
        "invocation": {
            "verified": False,
            "connection_url": connection_url,
        },
    }


def _resolve_evaluation_candidate(req: "CreateRequest") -> dict[str, Any]:
    """Resolve a concrete evaluation candidate for delegated validation."""
    return _resolve_delegation_candidate(
        capability_family="evaluation",
        requested_agent_id=req.evaluation_agent_id,
        connection_id=req.evaluation_connection_id,
        connection_url=req.evaluation_connection_url,
        include_live_results=req.evaluation_include_live_results,
        default_name="Unresolved Evaluation Agent",
    )


def _resolve_execution_candidate(req: "CreateRequest") -> dict[str, Any]:
    """Resolve a concrete execution candidate for delegated execution."""
    return _resolve_delegation_candidate(
        capability_family="execution",
        requested_agent_id=req.execution_agent_id,
        connection_id=req.execution_connection_id,
        connection_url=req.execution_connection_url,
        include_live_results=req.execution_include_live_results,
        default_name="Unresolved Execution Agent",
    )


def _build_evaluation_payload(task_response: dict[str, Any]) -> dict[str, Any]:
    """Build the delegated evaluation payload from the normalized task result."""
    return {
        "service": task_response.get("service"),
        "assignment": task_response.get("assignment"),
        "route": task_response.get("route"),
        "artifacts": task_response.get("artifacts", []),
        "details": {
            "files_created": task_response.get("details", {}).get("files_created", []),
            "files_uploaded": task_response.get("details", {}).get("files_uploaded"),
            "course_context_count": len(task_response.get("details", {}).get("course_context", [])),
        },
    }


def _build_delegation_blocked_result(
    *,
    candidate: dict[str, Any],
    payload: dict[str, Any],
    tool_name: str,
    subtask_id: str,
    outcome_field: str,
    policy: dict[str, Any],
    connection_id: Optional[str],
    connection_url: Optional[str],
) -> dict[str, Any]:
    now = _utcnow_iso()
    return {
        "status": "blocked",
        "subtask_id": subtask_id,
        "agent": {
            "agent_id": candidate.get("agent_id"),
            "name": candidate.get("name"),
            "source": candidate.get("source"),
            "protocols": candidate.get("protocols", []),
            "connection_id": connection_id,
            "connection_url": connection_url or candidate.get("invocation", {}).get("connection_url"),
        },
        "request_summary": {
            "requested_tool_name": tool_name,
            "tool_name": tool_name,
            "artifact_count": len(payload.get("artifacts", [])),
            "assignment_name": payload.get("assignment", {}).get("name"),
        },
        "tool_selection": None,
        "artifacts": [],
        outcome_field: {
            "status": "blocked",
            "response": None,
        },
        "errors": {
            "message": "Delegation policy blocked remote execution.",
        },
        "policy": policy,
        "timing": {
            "started_at": now,
            "completed_at": now,
        },
    }


async def _maybe_attach_delegated_execution(
    req: "CreateRequest",
    task_response: dict[str, Any],
    *,
    task_id: Optional[str] = None,
) -> dict[str, Any]:
    """Optionally run delegated execution and attach the result."""
    should_execute = req.enable_delegated_execution or delegated_execution_enabled_by_default()
    if not should_execute:
        return task_response

    candidate = _resolve_execution_candidate(req)
    scorecard = TASK_STORE.get_agent_scorecard(candidate.get("agent_id", ""), "execution") if candidate.get("agent_id") else None
    explicit_request = any(
        [
            req.execution_agent_id,
            req.execution_connection_id,
            req.execution_connection_url,
        ]
    )
    policy = evaluate_delegation_policy(
        capability_family="execution",
        candidate=candidate,
        connection_id=req.execution_connection_id,
        connection_url=req.execution_connection_url,
        explicit_request=explicit_request,
        scorecard=scorecard,
    )

    if task_id:
        _save_task_step(
            task_id,
            _build_task_step(
                task_id=task_id,
                step_id="execute_generated_project",
                title="Execute generated project",
                position=2,
                mode="delegated",
                capability_family="execution",
                status="running" if policy["allowed"] else "blocked",
                started_at=_utcnow_iso(),
                agent={
                    "agent_id": candidate.get("agent_id"),
                    "name": candidate.get("name"),
                },
                policy=policy,
            ),
        )

    if not policy["allowed"]:
        execution_result = _build_delegation_blocked_result(
            candidate=candidate,
            payload=_build_evaluation_payload(task_response),
            tool_name=req.execution_tool_name,
            subtask_id="execute_generated_project",
            outcome_field="execution",
            policy=policy,
            connection_id=req.execution_connection_id,
            connection_url=req.execution_connection_url,
        )
    else:
        execution_result = await REMOTE_AGENT_CLIENT.execute_assignment_output(
            candidate=candidate,
            payload=_build_evaluation_payload(task_response),
            connection_id=req.execution_connection_id,
            connection_url=req.execution_connection_url,
            tool_name=req.execution_tool_name,
        )
        execution_result["policy"] = policy

    task_response["details"]["delegated_execution"] = execution_result
    task_response["details"].setdefault("delegation_policy", {})["execution"] = policy
    _record_agent_scorecard_event(task_id, execution_result, "execution")

    if task_id:
        status = execution_result.get("status")
        _save_task_step(
            task_id,
            _build_task_step(
                task_id=task_id,
                step_id="execute_generated_project",
                title="Execute generated project",
                position=2,
                mode="delegated",
                capability_family="execution",
                status=status,
                started_at=execution_result.get("timing", {}).get("started_at"),
                completed_at=execution_result.get("timing", {}).get("completed_at") if status == "completed" else None,
                failed_at=execution_result.get("timing", {}).get("completed_at") if status in {"failed", "blocked"} else None,
                agent=execution_result.get("agent"),
                policy=policy,
                summary={
                    **(execution_result.get("request_summary") or {}),
                    "tool_selection": execution_result.get("tool_selection"),
                },
                result=execution_result.get("execution"),
                error=execution_result.get("errors"),
            ),
        )

    return task_response


async def _maybe_attach_delegated_evaluation(
    req: "CreateRequest",
    task_response: dict[str, Any],
    *,
    task_id: Optional[str] = None,
) -> dict[str, Any]:
    """Optionally run delegated evaluation and attach provenance."""
    should_evaluate = req.enable_delegated_evaluation or delegated_evaluation_enabled_by_default()
    if not should_evaluate:
        task_response["details"]["artifact_provenance"] = build_artifact_provenance(
            task_response,
            delegated_execution=task_response["details"].get("delegated_execution"),
        )
        return task_response

    candidate = _resolve_evaluation_candidate(req)
    scorecard = TASK_STORE.get_agent_scorecard(candidate.get("agent_id", ""), "evaluation") if candidate.get("agent_id") else None
    explicit_request = any(
        [
            req.evaluation_agent_id,
            req.evaluation_connection_id,
            req.evaluation_connection_url,
        ]
    )
    policy = evaluate_delegation_policy(
        capability_family="evaluation",
        candidate=candidate,
        connection_id=req.evaluation_connection_id,
        connection_url=req.evaluation_connection_url,
        explicit_request=explicit_request,
        scorecard=scorecard,
    )

    if task_id:
        _save_task_step(
            task_id,
            _build_task_step(
                task_id=task_id,
                step_id="validate_generated_project",
                title="Validate generated project",
                position=3,
                mode="delegated",
                capability_family="evaluation",
                status="running" if policy["allowed"] else "blocked",
                started_at=_utcnow_iso(),
                agent={
                    "agent_id": candidate.get("agent_id"),
                    "name": candidate.get("name"),
                },
                policy=policy,
            ),
        )

    if not policy["allowed"]:
        evaluation_result = _build_delegation_blocked_result(
            candidate=candidate,
            payload=_build_evaluation_payload(task_response),
            tool_name=req.evaluation_tool_name,
            subtask_id="validate_generated_project",
            outcome_field="validation",
            policy=policy,
            connection_id=req.evaluation_connection_id,
            connection_url=req.evaluation_connection_url,
        )
    else:
        evaluation_result = await REMOTE_AGENT_CLIENT.evaluate_assignment_output(
            candidate=candidate,
            payload=_build_evaluation_payload(task_response),
            connection_id=req.evaluation_connection_id,
            connection_url=req.evaluation_connection_url,
            tool_name=req.evaluation_tool_name,
        )
        evaluation_result["policy"] = policy

    task_response["details"]["delegated_evaluation"] = evaluation_result
    task_response["details"].setdefault("delegation_policy", {})["evaluation"] = policy
    _record_agent_scorecard_event(task_id, evaluation_result, "evaluation")
    task_response = _refresh_artifact_provenance(task_response)

    if task_id:
        status = evaluation_result.get("status")
        _save_task_step(
            task_id,
            _build_task_step(
                task_id=task_id,
                step_id="validate_generated_project",
                title="Validate generated project",
                position=3,
                mode="delegated",
                capability_family="evaluation",
                status=status,
                started_at=evaluation_result.get("timing", {}).get("started_at"),
                completed_at=evaluation_result.get("timing", {}).get("completed_at") if status == "completed" else None,
                failed_at=evaluation_result.get("timing", {}).get("completed_at") if status in {"failed", "blocked"} else None,
                agent=evaluation_result.get("agent"),
                policy=policy,
                summary={
                    **(evaluation_result.get("request_summary") or {}),
                    "tool_selection": evaluation_result.get("tool_selection"),
                },
                result=evaluation_result.get("validation"),
                error=evaluation_result.get("errors"),
            ),
        )

    return task_response


def _schedule_task_execution(task_id: str, req: "CreateRequest") -> None:
    asyncio.create_task(_execute_task(task_id, req))


def _schedule_task_resume(
    task_id: str,
    req: "CreateRequest",
    step_ids: list[str],
    *,
    force_full_rerun: bool = False,
) -> None:
    asyncio.create_task(_resume_task_execution(task_id, req, step_ids, force_full_rerun=force_full_rerun))


def _resolve_resume_step_ids(task_id: str, requested_step_ids: Optional[list[str]]) -> list[str]:
    if requested_step_ids:
        return list(dict.fromkeys(step_id.strip() for step_id in requested_step_ids if step_id and step_id.strip()))

    failed_steps = [
        step.get("step_id")
        for step in TASK_STORE.list_steps(task_id)
        if step.get("status") in {"failed", "blocked"}
    ]
    return [step_id for step_id in failed_steps if step_id]


async def _resume_task_execution(
    task_id: str,
    req: "CreateRequest",
    step_ids: list[str],
    *,
    force_full_rerun: bool = False,
) -> None:
    task = TASK_STORE.get(task_id)
    if not task:
        return

    full_rerun = force_full_rerun or not task.get("result") or "generate_primary_artifacts" in step_ids or task.get("status") == "failed"
    if full_rerun:
        task["status"] = "running"
        task["started_at"] = _utcnow_iso()
        task["completed_at"] = None
        task["failed_at"] = None
        task["error"] = None
        task["result"] = None
        TASK_STORE[task_id] = task
        await _execute_task(task_id, req)
        return

    task["status"] = "running"
    task["error"] = None
    task["failed_at"] = None
    TASK_STORE[task_id] = task

    try:
        task_response = dict(task.get("result") or {})
        task_response["details"] = dict(task_response.get("details") or {})

        if "execute_generated_project" in step_ids:
            task_response = await _maybe_attach_delegated_execution(req, task_response, task_id=task_id)
        if "validate_generated_project" in step_ids:
            task_response = await _maybe_attach_delegated_evaluation(req, task_response, task_id=task_id)
        else:
            task_response = _refresh_artifact_provenance(task_response)

        task["status"] = "completed"
        task["completed_at"] = _utcnow_iso()
        task["result"] = task_response
        TASK_STORE[task_id] = task
    except Exception:
        logger.exception("Failed to resume task_id=%s", task_id)
        task["status"] = "failed"
        task["failed_at"] = _utcnow_iso()
        task["error"] = {
            "code": "task_resume_failed",
            "message": "Task resume failed.",
        }
        TASK_STORE[task_id] = task


async def _execute_task(task_id: str, req: "CreateRequest") -> None:
    task = TASK_STORE.get(task_id)
    if not task:
        return

    task["status"] = "running"
    task["started_at"] = _utcnow_iso()
    task["error"] = None
    TASK_STORE[task_id] = task

    try:
        _save_task_step(
            task_id,
            _build_task_step(
                task_id=task_id,
                step_id="generate_primary_artifacts",
                title="Generate primary artifacts",
                position=1,
                mode="local",
                status="running",
                started_at=_utcnow_iso(),
                agent={
                    "type": "service",
                    "name": SERVICE_NAME,
                    "slug": SERVICE_SLUG,
                },
            ),
        )
        owner_id = task.get("owner_user_id")
        task_creds = _credentials_for_task_owner(owner_id) if owner_id is not None else None
        agent = CanvasGitHubAgent(credentials=task_creds) if task_creds else CanvasGitHubAgent()
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
            _save_task_step(
                task_id,
                _build_task_step(
                    task_id=task_id,
                    step_id="generate_primary_artifacts",
                    title="Generate primary artifacts",
                    position=1,
                    mode="local",
                    status="failed",
                    started_at=task.get("started_at"),
                    failed_at=task["failed_at"],
                    agent={
                        "type": "service",
                        "name": SERVICE_NAME,
                        "slug": SERVICE_SLUG,
                    },
                    error=task["error"],
                ),
            )
            TASK_STORE[task_id] = task
            return

        task["status"] = "completed"
        task["completed_at"] = _utcnow_iso()
        task_response = _build_task_response(req, result)
        _save_task_step(
            task_id,
            _build_task_step(
                task_id=task_id,
                step_id="generate_primary_artifacts",
                title="Generate primary artifacts",
                position=1,
                mode="local",
                status="completed",
                started_at=task.get("started_at"),
                completed_at=task["completed_at"],
                agent={
                    "type": "service",
                    "name": SERVICE_NAME,
                    "slug": SERVICE_SLUG,
                },
                summary={
                    "artifact_count": len(task_response.get("artifacts", [])),
                    "destination": task_response.get("route", {}).get("destination"),
                },
            ),
        )
        task_response = await _maybe_attach_delegated_execution(req, task_response, task_id=task_id)
        task["result"] = await _maybe_attach_delegated_evaluation(req, task_response, task_id=task_id)
        TASK_STORE[task_id] = task
    except Exception:
        logger.exception("Failed to execute task_id=%s", task_id)
        task["status"] = "failed"
        task["failed_at"] = _utcnow_iso()
        task["error"] = {
            "code": "internal_execution_error",
            "message": "Task execution failed.",
        }
        _save_task_step(
            task_id,
            _build_task_step(
                task_id=task_id,
                step_id="generate_primary_artifacts",
                title="Generate primary artifacts",
                position=1,
                mode="local",
                status="failed",
                started_at=task.get("started_at"),
                failed_at=task["failed_at"],
                agent={
                    "type": "service",
                    "name": SERVICE_NAME,
                    "slug": SERVICE_SLUG,
                },
                error=task["error"],
            ),
        )
        TASK_STORE[task_id] = task


app = FastAPI(title="Canvas Assignment Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateRequest(BaseModel):
    course_id: int
    assignment_id: Optional[int] = None
    language: str = "python"
    assignment_type: Optional[str] = None
    notion_content_mode: Optional[str] = None
    enable_delegated_evaluation: bool = False
    evaluation_agent_id: Optional[str] = None
    evaluation_connection_id: Optional[str] = None
    evaluation_connection_url: Optional[str] = None
    evaluation_tool_name: str = "evaluate"
    evaluation_include_live_results: bool = False
    enable_delegated_execution: bool = False
    execution_agent_id: Optional[str] = None
    execution_connection_id: Optional[str] = None
    execution_connection_url: Optional[str] = None
    execution_tool_name: str = "execute"
    execution_include_live_results: bool = False


class CourseDocumentIngestRequest(BaseModel):
    file_path: str
    document_name: Optional[str] = None


class CourseContextSearchRequest(BaseModel):
    query: str
    limit: int = 5


class DiscoverAgentsRequest(BaseModel):
    capability_family: Optional[str] = None
    query: Optional[str] = None
    limit: int = 5
    include_live_results: bool = False
    verified_only: bool = False


class ResumeTaskRequest(BaseModel):
    step_ids: Optional[list[str]] = None
    force_full_rerun: bool = False


class DelegationToolInspectionRequest(BaseModel):
    capability_family: str


class ConnectTokensBody(BaseModel):
    canvas_token: str
    github_token: str
    github_username: str


@app.post("/auth/session")
async def auth_create_or_update_session(body: ConnectTokensBody, request: Request, response: Response):
    """Store encrypted Canvas and GitHub tokens; set session cookie."""
    if not session_auth_enabled():
        raise HTTPException(
            status_code=501,
            detail="Per-user sessions are not configured. Set CREDENTIAL_ENCRYPTION_KEY (Fernet key).",
        )
    if not (body.canvas_token or "").strip() or not (body.github_token or "").strip():
        raise HTTPException(status_code=400, detail="canvas_token and github_token are required.")
    if not (body.github_username or "").strip():
        raise HTTPException(status_code=400, detail="github_username is required.")
    raw_existing = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_existing and USER_STORE.validate_session(raw_existing) is not None:
        USER_STORE.update_credentials_for_session(
            raw_existing,
            canvas_token=body.canvas_token.strip(),
            github_token=body.github_token.strip(),
            github_username=body.github_username.strip(),
        )
        return {"status": "ok", "updated": True}
    raw_token, user_id = USER_STORE.create_session_with_credentials(
        canvas_token=body.canvas_token.strip(),
        github_token=body.github_token.strip(),
        github_username=body.github_username.strip(),
    )
    secure = os.getenv("SESSION_COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes"}
    max_age = max(SESSION_TTL_DAYS, 1) * 86400
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
        max_age=max_age,
        secure=secure,
        path="/",
    )
    return {"status": "ok", "updated": False, "user_id": user_id}


@app.get("/auth/status")
async def auth_status(request: Request):
    """Report whether session-based auth is enabled and whether this browser has a session."""
    if not session_auth_enabled():
        return {
            "session_auth_enabled": False,
            "authenticated": False,
            "canvas_institution_url": get_canvas_institution_url(),
        }
    uid = optional_session_user_id(request)
    return {
        "session_auth_enabled": True,
        "authenticated": uid is not None,
        "canvas_institution_url": get_canvas_institution_url(),
    }


@app.delete("/auth/session")
async def auth_delete_session(request: Request, response: Response):
    """Clear session cookie and remove server-side session row."""
    raw = request.cookies.get(SESSION_COOKIE_NAME)
    USER_STORE.delete_session(raw)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}


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


async def _discover_agents_body(req: DiscoverAgentsRequest) -> dict[str, Any]:
    try:
        candidates = await asyncio.to_thread(
            AGENT_REGISTRY.discover_agents,
            capability_family=req.capability_family,
            query=req.query,
            limit=req.limit,
            include_live_results=req.include_live_results,
            verified_only=req.verified_only,
        )
        return _build_discovery_response(req, _attach_scorecards_to_candidates(candidates))
    except Exception:
        logger.exception(
            "Failed to discover agents for capability_family=%s query=%s",
            req.capability_family,
            req.query,
        )
        raise HTTPException(status_code=500, detail="Failed to discover agents.")


@app.post("/discover-agents")
async def discover_agents(req: DiscoverAgentsRequest, request: Request):
    """Return ranked candidate agents for the requested capability family or search query."""
    if session_auth_enabled():
        workflow_credentials_for_http(request)
    return await _discover_agents_body(req)


async def _plan_assignment_body(req: CreateRequest, creds: WorkflowCredentials) -> dict[str, Any]:
    try:
        plan_result = await generate_assignment_plan(
            course_id=req.course_id,
            assignment_id=req.assignment_id,
            language=req.language,
            assignment_type=req.assignment_type,
            notion_content_mode=req.notion_content_mode,
            agent_factory=CanvasGitHubAgent,
            credentials=creds,
        )
        plan_result["plan"]["delegation_candidates"] = AGENT_REGISTRY.enrich_capability_groups(
            plan_result["plan"]["delegation_candidates"],
            limit_per_group=3,
            include_live_results=False,
            verified_only=False,
        )
        for group in plan_result["plan"]["delegation_candidates"]:
            group["candidates"] = _attach_scorecards_to_candidates(group.get("candidates", []))
        return _build_plan_response(req, plan_result)
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        logger.exception(
            "Failed to plan assignment for course_id=%s assignment_id=%s",
            req.course_id,
            req.assignment_id,
        )
        raise HTTPException(status_code=500, detail="Failed to plan assignment.")


@app.post("/plan")
async def plan_assignment(req: CreateRequest, request: Request):
    """Analyze an assignment and return a structured execution plan."""
    creds = workflow_credentials_for_http(request)
    return await _plan_assignment_body(req, creds)


async def _enqueue_task(req: CreateRequest, owner_user_id: Optional[int]) -> dict[str, Any]:
    task_id = str(uuid4())
    TASK_STORE[task_id] = _build_task_status(
        task_id=task_id,
        request=_request_payload(req),
        status="queued",
        submitted_at=_utcnow_iso(),
        owner_user_id=owner_user_id,
    )
    _schedule_task_execution(task_id, req)
    return TASK_STORE[task_id]


@app.post("/tasks", status_code=202)
async def submit_task(req: CreateRequest, request: Request):
    """Queue assignment destination creation for asynchronous execution."""
    if session_auth_enabled() and optional_session_user_id(request) is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    owner_user_id = optional_session_user_id(request) if session_auth_enabled() else None
    return await _enqueue_task(req, owner_user_id)


async def _get_task_payload(task_id: str, request: Optional[Request]) -> dict[str, Any]:
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, request)
    return task


@app.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    """Return the status of a previously submitted task."""
    return await _get_task_payload(task_id, request)


@app.get("/tasks/{task_id}/steps")
async def get_task_steps(
    task_id: str,
    request: Request,
    status: Optional[str] = None,
    retried_only: bool = False,
    delegated_only: bool = False,
):
    """Return persisted execution steps for a task."""
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, request)
    steps = TASK_STORE.list_steps(task_id)
    if status:
        statuses = {item.strip().lower() for item in status.split(",") if item.strip()}
        steps = [step for step in steps if str(step.get("status") or "").lower() in statuses]
    if retried_only:
        steps = [step for step in steps if int(step.get("retry_count") or 0) > 0]
    if delegated_only:
        steps = [step for step in steps if step.get("mode") == "delegated"]
    return {
        "task_id": task_id,
        "filters": {
            "status": status,
            "retried_only": retried_only,
            "delegated_only": delegated_only,
        },
        "steps": steps,
    }


@app.get("/tasks/{task_id}/artifacts")
async def get_task_artifacts(task_id: str, request: Request):
    """Return generated artifacts and provenance for a task."""
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, request)

    result = task.get("result") or {}
    return {
        "task_id": task_id,
        "status": task.get("status"),
        "artifacts": result.get("artifacts", []),
        "provenance": result.get("details", {}).get("artifact_provenance", []),
    }


@app.post("/tasks/{task_id}/resume", status_code=202)
async def resume_task(task_id: str, req: ResumeTaskRequest, request: Request):
    """Resume a task, optionally retrying only selected failed or blocked steps."""
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, request)
    if task.get("status") in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Task is already queued or running.")

    step_ids = _resolve_resume_step_ids(task_id, req.step_ids)
    create_request = _create_request_from_payload(task.get("request") or {})
    full_rerun = req.force_full_rerun or not task.get("result") or "generate_primary_artifacts" in step_ids or task.get("status") == "failed"

    task["status"] = "queued"
    task["error"] = None
    if full_rerun:
        task["result"] = None
        task["completed_at"] = None
    TASK_STORE[task_id] = task

    _schedule_task_resume(task_id, create_request, step_ids, force_full_rerun=full_rerun)
    return TASK_STORE[task_id]


@app.post("/tasks/{task_id}/inspect-delegation-tool")
async def inspect_task_delegation_tool(task_id: str, req: DelegationToolInspectionRequest, request: Request):
    """Resolve the remote tool and schema that would be used for a delegated step."""
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, request)
    create_request = _create_request_from_payload(task.get("request") or {})
    try:
        return await _inspect_task_delegation_tool(task_id, create_request, req.capability_family)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to inspect delegation tool for task_id=%s capability_family=%s",
            task_id,
            req.capability_family,
        )
        raise HTTPException(status_code=500, detail="Failed to inspect delegation tool.")


@app.get("/agents/scorecards")
async def list_agent_scorecards(request: Request, capability_family: Optional[str] = None):
    """Return persisted delegation scorecards for known remote agents."""
    if session_auth_enabled():
        workflow_credentials_for_http(request)
    return {
        "scorecards": TASK_STORE.list_agent_scorecards(capability_family),
    }


async def _get_courses_core(creds: WorkflowCredentials) -> dict[str, Any]:
    try:
        canvas = _canvas_tools_from_credentials(creds)
        courses = await canvas.list_courses()
        return {"courses": courses}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list Canvas courses")
        raise HTTPException(status_code=500, detail="Failed to fetch courses.")


@app.get("/courses")
async def get_courses(request: Request):
    """Return all Canvas courses for the authenticated user."""
    return await _get_courses_core(workflow_credentials_for_http(request))


async def _get_assignments_core(course_id: int, creds: WorkflowCredentials) -> dict[str, Any]:
    try:
        canvas = _canvas_tools_from_credentials(creds)
        assignments = await canvas.get_course_assignments(course_id)
        return {"assignments": assignments}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list assignments for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to fetch assignments.")


@app.get("/courses/{course_id}/assignments")
async def get_assignments(course_id: int, request: Request):
    """Return all assignments for a given course."""
    return await _get_assignments_core(course_id, workflow_credentials_for_http(request))


async def _get_modules_core(course_id: int, creds: WorkflowCredentials) -> dict[str, Any]:
    try:
        canvas = _canvas_tools_from_credentials(creds)
        modules = await canvas.get_course_modules(course_id)
        return {"modules": modules}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list modules for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail="Failed to fetch modules.")


@app.get("/courses/{course_id}/modules")
async def get_modules(course_id: int, request: Request):
    """Return Canvas modules for a given course."""
    return await _get_modules_core(course_id, workflow_credentials_for_http(request))


async def _search_course_modules_core(
    course_id: int, req: CourseContextSearchRequest, creds: WorkflowCredentials
) -> dict[str, Any]:
    try:
        canvas = _canvas_tools_from_credentials(creds)
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


@app.post("/courses/{course_id}/modules/search")
async def search_course_modules(course_id: int, req: CourseContextSearchRequest, request: Request):
    """Search Canvas course modules for assignment-relevant context."""
    return await _search_course_modules_core(course_id, req, workflow_credentials_for_http(request))


@app.post("/courses/{course_id}/documents/ingest")
async def ingest_course_document(course_id: int, req: CourseDocumentIngestRequest, request: Request):
    """Parse a local course PDF and index it into Chroma."""
    if session_auth_enabled():
        workflow_credentials_for_http(request)
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
async def get_course_documents(course_id: int, request: Request):
    """List course documents currently indexed for retrieval."""
    if session_auth_enabled():
        workflow_credentials_for_http(request)
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
async def search_course_context(course_id: int, req: CourseContextSearchRequest, request: Request):
    """Search the Chroma-backed course context store for a course."""
    if session_auth_enabled():
        workflow_credentials_for_http(request)
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


async def _create_destination_core(req: CreateRequest, creds: WorkflowCredentials) -> dict[str, Any]:
    try:
        agent = CanvasGitHubAgent(credentials=creds)
        result = await agent.run(
            course_id=req.course_id,
            assignment_id=req.assignment_id,
            language=req.language,
            assignment_type=req.assignment_type,
            notion_content_mode=req.notion_content_mode,
        )
        if not result:
            raise HTTPException(status_code=400, detail="Agent failed to create destination.")
        task_response = _build_task_response(req, result)
        task_response = await _maybe_attach_delegated_execution(req, task_response)
        return await _maybe_attach_delegated_evaluation(req, task_response)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to create destination for course_id=%s assignment_id=%s",
            req.course_id,
            req.assignment_id,
        )
        raise HTTPException(status_code=500, detail="Failed to create destination.")


@app.post("/create")
async def create_destination(req: CreateRequest, request: Request):
    """Synchronously create the destination for a Canvas assignment."""
    creds = workflow_credentials_for_http(request)
    return await _create_destination_core(req, creds)


# --- MCP / programmatic entrypoints (process environment credentials only) ---


async def get_courses_tools() -> dict[str, Any]:
    return await _get_courses_core(workflow_credentials_for_env())


async def get_assignments_tools(course_id: int) -> dict[str, Any]:
    return await _get_assignments_core(course_id, workflow_credentials_for_env())


async def get_modules_tools(course_id: int) -> dict[str, Any]:
    return await _get_modules_core(course_id, workflow_credentials_for_env())


async def search_course_modules_tools(course_id: int, req: CourseContextSearchRequest) -> dict[str, Any]:
    return await _search_course_modules_core(course_id, req, workflow_credentials_for_env())


async def discover_agents_tools(req: DiscoverAgentsRequest) -> dict[str, Any]:
    return await _discover_agents_body(req)


async def plan_assignment_tools(req: CreateRequest) -> dict[str, Any]:
    return await _plan_assignment_body(req, workflow_credentials_for_env())


async def create_destination_tools(req: CreateRequest) -> dict[str, Any]:
    return await _create_destination_core(req, workflow_credentials_for_env())


async def submit_task_tools(req: CreateRequest) -> dict[str, Any]:
    return await _enqueue_task(req, None)


async def get_task_tools(task_id: str) -> dict[str, Any]:
    return await _get_task_payload(task_id, None)


async def get_task_steps_tools(
    task_id: str,
    status: Optional[str] = None,
    retried_only: bool = False,
    delegated_only: bool = False,
) -> dict[str, Any]:
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, None)
    steps = TASK_STORE.list_steps(task_id)
    if status:
        statuses = {item.strip().lower() for item in status.split(",") if item.strip()}
        steps = [step for step in steps if str(step.get("status") or "").lower() in statuses]
    if retried_only:
        steps = [step for step in steps if int(step.get("retry_count") or 0) > 0]
    if delegated_only:
        steps = [step for step in steps if step.get("mode") == "delegated"]
    return {
        "task_id": task_id,
        "filters": {
            "status": status,
            "retried_only": retried_only,
            "delegated_only": delegated_only,
        },
        "steps": steps,
    }


async def get_task_artifacts_tools(task_id: str) -> dict[str, Any]:
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, None)
    result = task.get("result") or {}
    return {
        "task_id": task_id,
        "status": task.get("status"),
        "artifacts": result.get("artifacts", []),
        "provenance": result.get("details", {}).get("artifact_provenance", []),
    }


async def resume_task_tools(task_id: str, req: ResumeTaskRequest) -> dict[str, Any]:
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, None)
    if task.get("status") in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Task is already queued or running.")
    step_ids = _resolve_resume_step_ids(task_id, req.step_ids)
    create_request = _create_request_from_payload(task.get("request") or {})
    full_rerun = req.force_full_rerun or not task.get("result") or "generate_primary_artifacts" in step_ids or task.get("status") == "failed"
    task["status"] = "queued"
    task["error"] = None
    if full_rerun:
        task["result"] = None
        task["completed_at"] = None
    TASK_STORE[task_id] = task
    _schedule_task_resume(task_id, create_request, step_ids, force_full_rerun=full_rerun)
    return TASK_STORE[task_id]


async def inspect_task_delegation_tool_tools(task_id: str, req: DelegationToolInspectionRequest) -> dict[str, Any]:
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    _assert_task_visible(task, None)
    create_request = _create_request_from_payload(task.get("request") or {})
    try:
        return await _inspect_task_delegation_tool(task_id, create_request, req.capability_family)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to inspect delegation tool for task_id=%s capability_family=%s",
            task_id,
            req.capability_family,
        )
        raise HTTPException(status_code=500, detail="Failed to inspect delegation tool.")


async def list_agent_scorecards_tools(capability_family: Optional[str] = None) -> dict[str, Any]:
    return {
        "scorecards": TASK_STORE.list_agent_scorecards(capability_family),
    }


async def ingest_course_document_tools(course_id: int, req: CourseDocumentIngestRequest) -> Any:
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


async def get_course_documents_tools(course_id: int) -> dict[str, Any]:
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


async def search_course_context_tools(course_id: int, req: CourseContextSearchRequest) -> dict[str, Any]:
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