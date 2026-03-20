import asyncio
import json
from uuid import UUID

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import api
from app import mcp_server


def _decode_tool_payload(result):
    content, structured = result
    assert len(content) == 1
    assert json.loads(content[0].text) == structured
    return structured


def _decode_resource_payload(result):
    assert len(result) == 1
    return json.loads(result[0].content)


class StubCanvasTools:
    async def list_courses(self):
        return [{"id": 1, "name": "Course One"}]

    async def get_course_assignments(self, course_id):
        return [{"id": 42, "name": f"Assignment for {course_id}"}]


class StubAgentSuccess:
    async def run(self, **kwargs):
        return {
            "destination": "github",
            "assignment": {
                "id": kwargs.get("assignment_id") or 777,
                "name": "Homework 1",
                "due_at": "2026-03-30T12:00:00Z",
                "workflow_state": "unsubmitted",
                "is_completed": False,
            },
            "repository": {"html_url": "https://example.com/repo"},
            "files_created": ["README.md", "main.py"],
            "files_uploaded": True,
        }


class StubTaskScheduler:
    def __init__(self):
        self.calls = []

    def __call__(self, task_id, req):
        self.calls.append((task_id, req))


def test_server_lists_expected_tools_and_resources():
    async def _exercise_registry():
        tools = await mcp_server.server.list_tools()
        resources = await mcp_server.server.list_resources()
        return tools, resources

    tools, resources = asyncio.run(_exercise_registry())

    assert [tool.name for tool in tools] == [
        "list_courses",
        "list_assignments",
        "get_capabilities",
        "get_oasf_record",
        "create_destination",
        "submit_task",
        "get_task_status",
    ]
    assert [str(resource.uri) for resource in resources] == [
        "canvas-assignment-workflow://capabilities",
        "canvas-assignment-workflow://metadata/oasf-record",
    ]


def test_list_courses_tool(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)

    result = asyncio.run(mcp_server.server.call_tool("list_courses", {}))

    assert _decode_tool_payload(result) == {
        "courses": [{"id": 1, "name": "Course One"}],
    }


def test_create_destination_tool(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)

    result = asyncio.run(
        mcp_server.server.call_tool(
            "create_destination",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "assignment_type": "coding",
            },
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["status"] == "completed"
    assert payload["route"]["destination"] == "github"
    assert payload["artifacts"][0]["url"] == "https://example.com/repo"


def test_submit_task_and_get_task_status_tools(monkeypatch):
    api.TASK_STORE.clear()
    scheduler = StubTaskScheduler()
    monkeypatch.setattr(api, "_schedule_task_execution", scheduler)

    result = asyncio.run(
        mcp_server.server.call_tool(
            "submit_task",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "assignment_type": "coding",
            },
        )
    )

    payload = _decode_tool_payload(result)
    UUID(payload["task_id"])
    assert payload["status"] == "queued"
    assert len(scheduler.calls) == 1

    task_result = asyncio.run(
        mcp_server.server.call_tool(
            "get_task_status",
            {"task_id": payload["task_id"]},
        )
    )
    task_payload = _decode_tool_payload(task_result)
    assert task_payload["task_id"] == payload["task_id"]
    assert task_payload["status"] == "queued"


def test_get_task_status_tool_raises_for_missing_task():
    api.TASK_STORE.clear()

    with pytest.raises(ToolError, match="Task not found"):
        asyncio.run(
            mcp_server.server.call_tool(
                "get_task_status",
                {"task_id": "missing-task"},
            )
        )


def test_capabilities_resource(monkeypatch):
    monkeypatch.setattr(api, "get_service_base_url", lambda: "https://agent.example.com")

    result = asyncio.run(
        mcp_server.server.read_resource("canvas-assignment-workflow://capabilities")
    )

    payload = _decode_resource_payload(result)
    assert payload["service"]["base_url"] == "https://agent.example.com"
    assert payload["transports"]["mcp_stdio"]["server_name"] == "canvas-assignment-workflow"


def test_oasf_record_resource(monkeypatch):
    monkeypatch.setattr(api, "get_service_base_url", lambda: "https://agent.example.com")

    result = asyncio.run(
        mcp_server.server.read_resource("canvas-assignment-workflow://metadata/oasf-record")
    )

    payload = _decode_resource_payload(result)
    assert payload["annotations"]["mcp_stdio_command"] == "canvas-github-agent-mcp"
    assert payload["annotations"]["capabilities_endpoint"] == "https://agent.example.com/capabilities"