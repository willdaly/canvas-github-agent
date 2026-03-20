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


def _create_request(
    *,
    course_id: int,
    assignment_id: Optional[int] = None,
    language: str = "python",
    assignment_type: Optional[str] = None,
    notion_content_mode: Optional[str] = None,
) -> api.CreateRequest:
    """Build a validated request payload shared with the HTTP surface."""
    return api.CreateRequest(
        course_id=course_id,
        assignment_id=assignment_id,
        language=language,
        assignment_type=assignment_type,
        notion_content_mode=notion_content_mode,
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
) -> dict[str, Any]:
    """Queue async workflow execution using the shared in-memory task store."""
    return await api.submit_task(
        _create_request(
            course_id=course_id,
            assignment_id=assignment_id,
            language=language,
            assignment_type=assignment_type,
            notion_content_mode=notion_content_mode,
        )
    )


@server.tool(description="Fetch the current task_status_v1 payload for a submitted task.")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Return the status of a previously submitted async task."""
    try:
        return await api.get_task(task_id)
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


def run() -> None:
    """Run the MCP server over stdio for MCP-compatible clients."""
    server.run(transport="stdio")


if __name__ == "__main__":
    run()