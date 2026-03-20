"""FastMCP server exposing the Canvas assignment workflow as MCP tools."""

import json
from typing import Any, Optional

from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

import api


MCP_SERVER_NAME = "canvas-assignment-workflow"
MCP_SERVER_COMMAND = "canvas-github-agent-mcp"

server = FastMCP(
    name=MCP_SERVER_NAME,
    instructions=(
        "Inspect Canvas courses and assignments, discover service metadata, and "
        "provision GitHub or Notion destinations for Canvas assignments."
    ),
)


def _pilot_execution_profile() -> dict[str, Any]:
    return {
        "profile_id": "smithery-execution-pilot",
        "schema_version": "1.0",
        "capability_family": "execution",
        "connection": {
            "id": "assignment-execution-pilot",
            "url": "https://example.run.tools",
        },
        "tool_resolution": {
            "requested_tool_name": "runner.execute",
            "intent_queries": [
                "execute assignment",
                "run tests",
                "run benchmark",
            ],
        },
        "delegation_env": {
            "DELEGATION_ALLOWED_CONNECTION_IDS": "assignment-execution-pilot",
            "DELEGATION_MIN_TRUST_LEVEL": "verified_profile",
            "DELEGATION_ENFORCE_SCORECARD_THRESHOLDS": "true",
            "DELEGATION_MIN_SCORECARD_SUCCESS_RATE": "0.6",
            "DELEGATION_MIN_SCORECARD_TOTAL_COUNT": "3",
        },
    }


def _create_request(
    *,
    course_id: int,
    assignment_id: Optional[int] = None,
    language: str = "python",
    assignment_type: Optional[str] = None,
    notion_content_mode: Optional[str] = None,
    enable_delegated_evaluation: bool = False,
    evaluation_agent_id: Optional[str] = None,
    evaluation_connection_id: Optional[str] = None,
    evaluation_connection_url: Optional[str] = None,
    evaluation_tool_name: str = "evaluate",
    evaluation_include_live_results: bool = False,
    enable_delegated_execution: bool = False,
    execution_agent_id: Optional[str] = None,
    execution_connection_id: Optional[str] = None,
    execution_connection_url: Optional[str] = None,
    execution_tool_name: str = "execute",
    execution_include_live_results: bool = False,
) -> api.CreateRequest:
    """Build a validated request payload shared with the HTTP surface."""
    return api.CreateRequest(
        course_id=course_id,
        assignment_id=assignment_id,
        language=language,
        assignment_type=assignment_type,
        notion_content_mode=notion_content_mode,
        enable_delegated_evaluation=enable_delegated_evaluation,
        evaluation_agent_id=evaluation_agent_id,
        evaluation_connection_id=evaluation_connection_id,
        evaluation_connection_url=evaluation_connection_url,
        evaluation_tool_name=evaluation_tool_name,
        evaluation_include_live_results=evaluation_include_live_results,
        enable_delegated_execution=enable_delegated_execution,
        execution_agent_id=execution_agent_id,
        execution_connection_id=execution_connection_id,
        execution_connection_url=execution_connection_url,
        execution_tool_name=execution_tool_name,
        execution_include_live_results=execution_include_live_results,
    )


def _raise_tool_error(exc: HTTPException) -> None:
    """Convert HTTP-oriented errors into plain MCP tool failures."""
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    raise ValueError(detail)


@server.tool(description="List Canvas courses visible to the configured user.")
async def list_courses() -> dict[str, Any]:
    """Return the configured user's Canvas courses."""
    try:
        return await api.get_courses()
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="List assignments for a Canvas course.")
async def list_assignments(course_id: int) -> dict[str, Any]:
    """Return assignments for a Canvas course."""
    try:
        return await api.get_assignments(course_id)
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="List Canvas modules and module items for a course.")
async def list_course_modules(course_id: int) -> dict[str, Any]:
    """Return Canvas modules for a course."""
    try:
        return await api.get_modules(course_id)
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Search Canvas course module content for assignment-relevant context.")
async def search_course_modules(course_id: int, query: str, limit: int = 5) -> dict[str, Any]:
    """Search Canvas module content for relevant context."""
    try:
        return await api.search_course_modules(
            course_id,
            api.CourseContextSearchRequest(query=query, limit=limit),
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Return the service capabilities payload used for discovery.")
async def get_capabilities() -> dict[str, Any]:
    """Return service capabilities and transport metadata."""
    return await api.get_capabilities()


@server.tool(description="Return the checked-in OASF record for this service.")
async def get_oasf_record() -> dict[str, Any]:
    """Return the service OASF record."""
    try:
        return await api.get_oasf_record()
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Parse a course PDF with Docling and index it into Chroma.")
async def ingest_course_document(
    course_id: int,
    file_path: str,
    document_name: Optional[str] = None,
) -> dict[str, Any]:
    """Ingest a course document for later retrieval."""
    try:
        return await api.ingest_course_document(
            course_id,
            api.CourseDocumentIngestRequest(file_path=file_path, document_name=document_name),
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="List course documents currently indexed for retrieval.")
async def list_course_documents(course_id: int) -> dict[str, Any]:
    """Return indexed course documents for a course."""
    try:
        return await api.get_course_documents(course_id)
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Search indexed course documents for assignment-relevant context.")
async def search_course_context(course_id: int, query: str, limit: int = 5) -> dict[str, Any]:
    """Search the course context store for relevant chunks."""
    try:
        return await api.search_course_context(
            course_id,
            api.CourseContextSearchRequest(query=query, limit=limit),
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Return ranked external agent candidates for a requested capability family or search query.")
async def discover_agents(
    capability_family: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 5,
    include_live_results: bool = False,
    verified_only: bool = False,
) -> dict[str, Any]:
    """Discover candidate external agents for delegation."""
    try:
        return await api.discover_agents(
            api.DiscoverAgentsRequest(
                capability_family=capability_family,
                query=query,
                limit=limit,
                include_live_results=include_live_results,
                verified_only=verified_only,
            )
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Analyze an assignment and return a structured execution plan without publishing artifacts.")
async def plan_assignment(
    course_id: int,
    assignment_id: Optional[int] = None,
    language: str = "python",
    assignment_type: Optional[str] = None,
    notion_content_mode: Optional[str] = None,
) -> dict[str, Any]:
    """Return the pre-execution assignment plan."""
    try:
        return await api.plan_assignment(
            _create_request(
                course_id=course_id,
                assignment_id=assignment_id,
                language=language,
                assignment_type=assignment_type,
                notion_content_mode=notion_content_mode,
            )
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(
    description=(
        "Synchronously create a GitHub repository for a coding assignment or a "
        "Notion page for a writing assignment."
    )
)
async def create_destination(
    course_id: int,
    assignment_id: Optional[int] = None,
    language: str = "python",
    assignment_type: Optional[str] = None,
    notion_content_mode: Optional[str] = None,
    enable_delegated_evaluation: bool = False,
    evaluation_agent_id: Optional[str] = None,
    evaluation_connection_id: Optional[str] = None,
    evaluation_connection_url: Optional[str] = None,
    evaluation_tool_name: str = "evaluate",
    evaluation_include_live_results: bool = False,
    enable_delegated_execution: bool = False,
    execution_agent_id: Optional[str] = None,
    execution_connection_id: Optional[str] = None,
    execution_connection_url: Optional[str] = None,
    execution_tool_name: str = "execute",
    execution_include_live_results: bool = False,
) -> dict[str, Any]:
    """Run the existing synchronous provisioning workflow."""
    try:
        return await api.create_destination(
            _create_request(
                course_id=course_id,
                assignment_id=assignment_id,
                language=language,
                assignment_type=assignment_type,
                notion_content_mode=notion_content_mode,
                enable_delegated_evaluation=enable_delegated_evaluation,
                evaluation_agent_id=evaluation_agent_id,
                evaluation_connection_id=evaluation_connection_id,
                evaluation_connection_url=evaluation_connection_url,
                evaluation_tool_name=evaluation_tool_name,
                evaluation_include_live_results=evaluation_include_live_results,
                enable_delegated_execution=enable_delegated_execution,
                execution_agent_id=execution_agent_id,
                execution_connection_id=execution_connection_id,
                execution_connection_url=execution_connection_url,
                execution_tool_name=execution_tool_name,
                execution_include_live_results=execution_include_live_results,
            )
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Queue destination creation and return a task_status_v1 payload.")
async def submit_task(
    course_id: int,
    assignment_id: Optional[int] = None,
    language: str = "python",
    assignment_type: Optional[str] = None,
    notion_content_mode: Optional[str] = None,
    enable_delegated_evaluation: bool = False,
    evaluation_agent_id: Optional[str] = None,
    evaluation_connection_id: Optional[str] = None,
    evaluation_connection_url: Optional[str] = None,
    evaluation_tool_name: str = "evaluate",
    evaluation_include_live_results: bool = False,
    enable_delegated_execution: bool = False,
    execution_agent_id: Optional[str] = None,
    execution_connection_id: Optional[str] = None,
    execution_connection_url: Optional[str] = None,
    execution_tool_name: str = "execute",
    execution_include_live_results: bool = False,
) -> dict[str, Any]:
    """Queue async workflow execution using the shared in-memory task store."""
    return await api.submit_task(
        _create_request(
            course_id=course_id,
            assignment_id=assignment_id,
            language=language,
            assignment_type=assignment_type,
            notion_content_mode=notion_content_mode,
            enable_delegated_evaluation=enable_delegated_evaluation,
            evaluation_agent_id=evaluation_agent_id,
            evaluation_connection_id=evaluation_connection_id,
            evaluation_connection_url=evaluation_connection_url,
            evaluation_tool_name=evaluation_tool_name,
            evaluation_include_live_results=evaluation_include_live_results,
            enable_delegated_execution=enable_delegated_execution,
            execution_agent_id=execution_agent_id,
            execution_connection_id=execution_connection_id,
            execution_connection_url=execution_connection_url,
            execution_tool_name=execution_tool_name,
            execution_include_live_results=execution_include_live_results,
        )
    )


@server.tool(description="Fetch the current task_status_v1 payload for a submitted task.")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Return the status of a previously submitted async task."""
    try:
        return await api.get_task(task_id)
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Resume a failed or partially completed task, optionally retrying selected steps only.")
async def resume_task(task_id: str, step_ids: Optional[list[str]] = None, force_full_rerun: bool = False) -> dict[str, Any]:
    """Resume a task and optionally retry selected steps only."""
    try:
        return await api.resume_task(
            task_id,
            api.ResumeTaskRequest(step_ids=step_ids, force_full_rerun=force_full_rerun),
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="Inspect which schema-compatible remote tool would be selected for a delegated execution or evaluation step on a task.")
async def inspect_task_delegation_tool(task_id: str, capability_family: str) -> dict[str, Any]:
    """Resolve the remote tool selection for a task without executing it."""
    try:
        return await api.inspect_task_delegation_tool(
            task_id,
            api.DelegationToolInspectionRequest(capability_family=capability_family),
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="List persisted delegation scorecards for discovered or invoked agents.")
async def list_agent_scorecards(capability_family: Optional[str] = None) -> dict[str, Any]:
    """Return persisted agent scorecards."""
    return await api.list_agent_scorecards(capability_family)


@server.tool(description="List persisted execution_step_v1 records for a submitted task.")
async def list_task_steps(
    task_id: str,
    status: Optional[str] = None,
    retried_only: bool = False,
    delegated_only: bool = False,
) -> dict[str, Any]:
    """Return task step records for a submitted async task."""
    try:
        return await api.get_task_steps(
            task_id,
            status=status,
            retried_only=retried_only,
            delegated_only=delegated_only,
        )
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.tool(description="List generated artifacts and provenance for a submitted task.")
async def list_task_artifacts(task_id: str) -> dict[str, Any]:
    """Return task artifacts and provenance for a submitted async task."""
    try:
        return await api.get_task_artifacts(task_id)
    except HTTPException as exc:
        _raise_tool_error(exc)


@server.resource(
    "canvas-assignment-workflow://capabilities",
    name="service-capabilities",
    description="Static JSON resource describing the service contract and transports.",
    mime_type="application/json",
)
async def capabilities_resource() -> str:
    """Expose capabilities as a machine-readable MCP resource."""
    return json.dumps(api.build_capabilities_payload(), indent=2)


@server.resource(
    "canvas-assignment-workflow://metadata/oasf-record",
    name="oasf-record",
    description="Static JSON resource containing the service-level OASF record.",
    mime_type="application/json",
)
async def oasf_record_resource() -> str:
    """Expose the OASF record as a machine-readable MCP resource."""
    return json.dumps(
        api.build_service_oasf_record(service_base_url=api.get_service_base_url()),
        indent=2,
    )


@server.resource(
    "canvas-assignment-workflow://schemas/execution-step-v1",
    name="execution-step-schema",
    description="Static JSON schema describing persisted execution_step_v1 task step records.",
    mime_type="application/json",
)
async def execution_step_schema_resource() -> str:
    """Expose the execution step schema as a machine-readable MCP resource."""
    return json.dumps(api.build_execution_step_schema(), indent=2)


@server.resource(
    "canvas-assignment-workflow://schemas/agent-scorecard-v1",
    name="agent-scorecard-schema",
    description="Static JSON schema describing persisted agent_scorecard_v1 records.",
    mime_type="application/json",
)
async def agent_scorecard_schema_resource() -> str:
    """Expose the agent scorecard schema as a machine-readable MCP resource."""
    return json.dumps(api.build_agent_scorecard_schema(), indent=2)


@server.resource(
    "canvas-assignment-workflow://schemas/resume-task-v1",
    name="resume-task-schema",
    description="Static JSON schema describing task resume request payloads.",
    mime_type="application/json",
)
async def resume_task_schema_resource() -> str:
    """Expose the resume task request schema as a machine-readable MCP resource."""
    return json.dumps(api.build_resume_task_schema(), indent=2)


@server.resource(
    "canvas-assignment-workflow://schemas/delegation-tool-inspection-v1",
    name="delegation-tool-inspection-schema",
    description="Static JSON schema describing delegation tool inspection responses.",
    mime_type="application/json",
)
async def delegation_tool_inspection_schema_resource() -> str:
    """Expose the delegation tool inspection schema as a machine-readable MCP resource."""
    return json.dumps(api.build_delegation_tool_inspection_schema(), indent=2)


@server.resource(
    "canvas-assignment-workflow://profiles/smithery-execution-pilot",
    name="smithery-execution-pilot",
    description="Static JSON profile describing the baseline Smithery execution pilot configuration.",
    mime_type="application/json",
)
async def smithery_execution_pilot_resource() -> str:
    """Expose the Smithery execution pilot profile as a machine-readable MCP resource."""
    return json.dumps(_pilot_execution_profile(), indent=2)


def run() -> None:
    """Run the MCP server over stdio for MCP-compatible clients."""
    server.run(transport="stdio")


if __name__ == "__main__":
    run()