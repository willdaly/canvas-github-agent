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

    async def get_course_modules(self, course_id):
        return [{"id": 7, "name": f"Module for {course_id}", "items": [{"id": 11, "title": "Bayes Review"}]}]

    async def search_course_module_context(self, course_id, query, limit):
        return [
            {
                "id": "module:123:7:11",
                "course_id": course_id,
                "document_name": "Canvas Module: Module for 123",
                "section_title": "Bayes Review",
                "item_type": "Page",
                "text": "Module: Bayes Review\n\nPosterior update explanation.",
            }
        ][:limit]


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

    async def fetch_assignment(self, course_id, assignment_id=None):
        return {
            "id": assignment_id or 777,
            "name": "Homework 1",
            "description": "Implement BFS and DFS for the maze.",
            "due_at": "2026-03-30T12:00:00Z",
            "workflow_state": "unsubmitted",
            "is_completed": False,
        }

    async def fetch_course_context(self, course_id, assignment, limit=5):
        return [
            {
                "document_name": "slides.pdf",
                "section_title": "Search Review",
                "text": "BFS explores breadth-first.",
            }
        ]

    def infer_assignment_type(self, assignment):
        return "coding"


class StubTaskScheduler:
    def __init__(self):
        self.calls = []

    def __call__(self, task_id, req):
        self.calls.append((task_id, req))


class StubCourseContextTools:
    def ingest_pdf(self, course_id, file_path, document_name=None):
        return {
            "status": "ingested",
            "course_id": course_id,
            "document_id": "slides",
            "document_name": document_name or "slides.pdf",
            "chunk_count": 2,
            "collection": "course-context",
            "storage_path": ".chroma",
        }

    def list_documents(self, course_id):
        return [{"course_id": course_id, "document_name": "slides.pdf", "chunk_count": 2}]

    def search_context(self, course_id, query, limit):
        return [{"course_id": course_id, "document_name": "slides.pdf", "section_title": "Bayes Review", "text": "Section: Bayes Review\n\nPosterior is proportional to prior times likelihood."}]


class StubAgentRegistry:
    def discover_agents(
        self,
        *,
        capability_family=None,
        query=None,
        limit=5,
        include_live_results=False,
        verified_only=False,
    ):
        agent_name = "Stub Evaluation Agent" if (capability_family or "evaluation") == "evaluation" else "Stub Execution Agent"
        agent_id = "stub-evaluation-agent" if (capability_family or "evaluation") == "evaluation" else "stub-execution-agent"
        return [
            {
                "agent_id": agent_id,
                "name": agent_name,
                "source": "test_registry",
                "capability_family": capability_family or "evaluation",
                "protocols": ["mcp"],
                "trust_level": "test",
                "capabilities": [capability_family or "evaluation"],
                "description": "Test discovery result.",
                "invocation": {"verified": True, "connection_url": "https://example.com/mcp"},
                "ranking": {"capability_fit": 1.0, "source_bonus": 1.0, "popularity": 0.0, "score": 1.0},
            }
        ][:limit]

    def enrich_capability_groups(
        self,
        groups,
        *,
        limit_per_group=3,
        include_live_results=False,
        verified_only=False,
    ):
        enriched = []
        for group in groups:
            enriched_group = dict(group)
            enriched_group["candidates"] = self.discover_agents(
                capability_family=group.get("capability") or group.get("preferred_capability"),
                limit=limit_per_group,
                include_live_results=include_live_results,
                verified_only=verified_only,
            )
            enriched.append(enriched_group)
        return enriched


class StubRemoteAgentClient:
    async def execute_assignment_output(
        self,
        *,
        candidate,
        payload,
        connection_id=None,
        connection_url=None,
        tool_name="execute",
    ):
        return {
            "status": "completed",
            "subtask_id": "execute_generated_project",
            "agent": {
                "agent_id": candidate.get("agent_id"),
                "name": candidate.get("name"),
                "source": candidate.get("source"),
                "protocols": candidate.get("protocols", []),
                "connection_id": connection_id or "stub-execution-agent",
                "connection_url": connection_url or candidate.get("invocation", {}).get("connection_url"),
            },
            "request_summary": {
                "requested_tool_name": tool_name,
                "tool_name": tool_name,
                "artifact_count": len(payload.get("artifacts", [])),
                "assignment_name": payload.get("assignment", {}).get("name"),
            },
            "tool_selection": {
                "tool_name": tool_name,
                "schema": {"inputSchema": {"type": "object"}},
                "connection_id": connection_id or "stub-execution-agent",
                "connection_url": connection_url or candidate.get("invocation", {}).get("connection_url"),
            },
            "artifacts": [],
            "execution": {"status": "completed", "response": {"tests_passed": True}},
            "errors": None,
            "timing": {
                "started_at": "2026-03-20T00:00:00Z",
                "completed_at": "2026-03-20T00:00:01Z",
            },
        }

    async def evaluate_assignment_output(
        self,
        *,
        candidate,
        payload,
        connection_id=None,
        connection_url=None,
        tool_name="evaluate",
    ):
        return {
            "status": "completed",
            "subtask_id": "validate_generated_project",
            "agent": {
                "agent_id": candidate.get("agent_id"),
                "name": candidate.get("name"),
                "source": candidate.get("source"),
                "protocols": candidate.get("protocols", []),
                "connection_id": connection_id or "stub-evaluation-agent",
                "connection_url": connection_url or candidate.get("invocation", {}).get("connection_url"),
            },
            "request_summary": {
                "requested_tool_name": tool_name,
                "tool_name": tool_name,
                "artifact_count": len(payload.get("artifacts", [])),
                "assignment_name": payload.get("assignment", {}).get("name"),
            },
            "tool_selection": {
                "tool_name": tool_name,
                "schema": {"inputSchema": {"type": "object"}},
                "connection_id": connection_id or "stub-evaluation-agent",
                "connection_url": connection_url or candidate.get("invocation", {}).get("connection_url"),
            },
            "artifacts": [],
            "validation": {"status": "completed", "response": {"score": 0.91}},
            "errors": None,
            "timing": {
                "started_at": "2026-03-20T00:00:00Z",
                "completed_at": "2026-03-20T00:00:01Z",
            },
        }


def test_server_lists_expected_tools_and_resources():
    async def _exercise_registry():
        tools = await mcp_server.server.list_tools()
        resources = await mcp_server.server.list_resources()
        return tools, resources

    tools, resources = asyncio.run(_exercise_registry())

    assert [tool.name for tool in tools] == [
        "list_courses",
        "list_assignments",
        "list_course_modules",
        "search_course_modules",
        "get_capabilities",
        "get_oasf_record",
        "ingest_course_document",
        "list_course_documents",
        "search_course_context",
        "discover_agents",
        "plan_assignment",
        "create_destination",
        "submit_task",
        "get_task_status",
        "resume_task",
        "inspect_task_delegation_tool",
        "list_agent_scorecards",
        "list_task_steps",
        "list_task_artifacts",
    ]
    assert [str(resource.uri) for resource in resources] == [
        "canvas-assignment-workflow://capabilities",
        "canvas-assignment-workflow://metadata/oasf-record",
        "canvas-assignment-workflow://schemas/execution-step-v1",
        "canvas-assignment-workflow://schemas/agent-scorecard-v1",
        "canvas-assignment-workflow://schemas/resume-task-v1",
        "canvas-assignment-workflow://schemas/delegation-tool-inspection-v1",
        "canvas-assignment-workflow://profiles/smithery-execution-pilot",
    ]


def test_list_courses_tool(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)

    result = asyncio.run(mcp_server.server.call_tool("list_courses", {}))

    assert _decode_tool_payload(result) == {
        "courses": [{"id": 1, "name": "Course One"}],
    }


def test_list_course_modules_tool(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)

    result = asyncio.run(mcp_server.server.call_tool("list_course_modules", {"course_id": 123}))

    payload = _decode_tool_payload(result)
    assert payload["modules"][0]["name"] == "Module for 123"


def test_search_course_modules_tool(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)

    result = asyncio.run(
        mcp_server.server.call_tool(
            "search_course_modules",
            {"course_id": 123, "query": "posterior update", "limit": 1},
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["results"][0]["section_title"] == "Bayes Review"


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


def test_create_destination_tool_with_delegated_evaluation(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())

    result = asyncio.run(
        mcp_server.server.call_tool(
            "create_destination",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "assignment_type": "coding",
                "enable_delegated_evaluation": True,
                "evaluation_agent_id": "stub-evaluation-agent",
                "evaluation_connection_id": "stub-evaluation-agent",
            },
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["details"]["delegated_evaluation"]["status"] == "completed"
    assert payload["details"]["artifact_provenance"][-1]["kind"] == "delegated_evaluation"


def test_create_destination_tool_with_delegated_execution(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())

    result = asyncio.run(
        mcp_server.server.call_tool(
            "create_destination",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "assignment_type": "coding",
                "enable_delegated_execution": True,
                "execution_agent_id": "stub-execution-agent",
                "execution_connection_id": "stub-execution-agent",
            },
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["details"]["delegated_execution"]["status"] == "completed"
    assert payload["details"]["artifact_provenance"][-1]["kind"] == "delegated_execution"


def test_discover_agents_tool(monkeypatch):
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())

    result = asyncio.run(
        mcp_server.server.call_tool(
            "discover_agents",
            {
                "capability_family": "evaluation",
                "limit": 1,
            },
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["status"] == "ok"
    assert payload["candidates"][0]["name"] == "Stub Evaluation Agent"


def test_plan_assignment_tool(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())

    result = asyncio.run(
        mcp_server.server.call_tool(
            "plan_assignment",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
            },
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["status"] == "planned"
    assert payload["plan"]["domain"] == "maze_search"
    assert payload["recommendations"]


def test_search_course_context_tool(monkeypatch):
    monkeypatch.setattr(api, "CourseContextTools", StubCourseContextTools)

    result = asyncio.run(
        mcp_server.server.call_tool(
            "search_course_context",
            {"course_id": 123, "query": "posterior update", "limit": 1},
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["results"][0]["section_title"] == "Bayes Review"


def test_ingest_course_document_tool(monkeypatch):
    monkeypatch.setattr(api, "CourseContextTools", StubCourseContextTools)

    result = asyncio.run(
        mcp_server.server.call_tool(
            "ingest_course_document",
            {"course_id": 123, "file_path": "docs/slides.pdf", "document_name": "AAI Slides"},
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["status"] == "ingested"
    assert payload["document_name"] == "AAI Slides"


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


def test_resume_task_tool(monkeypatch):
    api.TASK_STORE.clear()
    scheduler = []

    def _schedule(task_id, req, step_ids, force_full_rerun=False):
        scheduler.append((task_id, step_ids, force_full_rerun))

    monkeypatch.setattr(api, "_schedule_task_resume", _schedule)
    req = api.CreateRequest(course_id=123, assignment_id=777, language="python")
    api.TASK_STORE["task-resume"] = api._build_task_status(
        task_id="task-resume",
        request=api._request_payload(req),
        status="completed",
        submitted_at="2026-03-20T00:00:00Z",
        result={"artifacts": [], "details": {}},
    )
    api.TASK_STORE.save_step(
        "task-resume",
        {
            "task_id": "task-resume",
            "step_id": "validate_generated_project",
            "title": "Validate generated project",
            "position": 3,
            "mode": "delegated",
            "capability_family": "evaluation",
            "status": "failed",
            "started_at": "2026-03-20T00:00:00Z",
            "completed_at": None,
            "failed_at": "2026-03-20T00:00:01Z",
            "agent": None,
            "policy": None,
            "summary": None,
            "result": None,
            "error": {"message": "failed"},
        },
    )

    result = asyncio.run(
        mcp_server.server.call_tool(
            "resume_task",
            {"task_id": "task-resume", "step_ids": ["validate_generated_project"]},
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["status"] == "queued"
    assert scheduler[0][1] == ["validate_generated_project"]


def test_inspect_task_delegation_tool(monkeypatch):
    api.TASK_STORE.clear()

    class InspectingRemoteAgentClient(StubRemoteAgentClient):
        async def inspect_assignment_tool(self, **kwargs):
            return {
                "tool_name": "runner.execute",
                "schema": {"inputSchema": {"type": "object"}},
                "connection_id": kwargs["connection_id"],
                "connection_url": kwargs["connection_url"],
            }

    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", InspectingRemoteAgentClient())

    req = api.CreateRequest(
        course_id=123,
        assignment_id=777,
        language="python",
        enable_delegated_execution=True,
        execution_agent_id="stub-execution-agent",
        execution_connection_id="stub-execution-agent",
    )
    api.TASK_STORE["task-inspect"] = api._build_task_status(
        task_id="task-inspect",
        request=api._request_payload(req),
        status="completed",
        submitted_at="2026-03-20T00:00:00Z",
        result={
            "status": "completed",
            "service": {"name": "Canvas Assignment Workflow", "slug": "canvas-assignment-workflow", "version": "0.1.0"},
            "request": api._request_payload(req),
            "route": {"destination": "github", "assignment_type": "coding", "language": "python", "notion_content_mode": None},
            "assignment": {"id": 777, "name": "Homework 1"},
            "artifacts": [{"kind": "github_repository", "url": "https://example.com/repo"}],
            "details": {},
        },
    )

    result = asyncio.run(
        mcp_server.server.call_tool(
            "inspect_task_delegation_tool",
            {"task_id": "task-inspect", "capability_family": "execution"},
        )
    )

    payload = _decode_tool_payload(result)
    assert payload["tool_selection"]["tool_name"] == "runner.execute"


def test_list_agent_scorecards_tool():
    api.TASK_STORE.clear()
    api.TASK_STORE.record_agent_scorecard_event(
        agent_id="stub-evaluation-agent",
        capability_family="evaluation",
        status="completed",
        tool_name="grader.evaluate",
        task_id="task-1",
        step_id="validate_generated_project",
    )

    result = asyncio.run(mcp_server.server.call_tool("list_agent_scorecards", {"capability_family": "evaluation"}))
    payload = _decode_tool_payload(result)
    assert payload["scorecards"][0]["agent_id"] == "stub-evaluation-agent"


def test_list_task_steps_and_artifacts_tools():
    api.TASK_STORE.clear()
    api.TASK_STORE["task-observe"] = api._build_task_status(
        task_id="task-observe",
        request={"course_id": 123},
        status="completed",
        submitted_at="2026-03-20T00:00:00Z",
        result={
            "artifacts": [{"kind": "github_repository", "url": "https://example.com/repo"}],
            "details": {"artifact_provenance": [{"artifact_id": "artifact-1", "kind": "github_repository"}]},
        },
    )
    api.TASK_STORE.save_step(
        "task-observe",
        {
            "task_id": "task-observe",
            "step_id": "generate_primary_artifacts",
            "title": "Generate primary artifacts",
            "position": 1,
            "mode": "local",
            "capability_family": None,
            "status": "completed",
            "started_at": "2026-03-20T00:00:00Z",
            "completed_at": "2026-03-20T00:00:01Z",
            "failed_at": None,
            "agent": {"type": "service", "name": "Canvas Assignment Workflow"},
            "policy": None,
            "summary": {"artifact_count": 1},
            "result": None,
            "error": None,
        },
    )

    steps_result = asyncio.run(
        mcp_server.server.call_tool(
            "list_task_steps",
            {"task_id": "task-observe", "delegated_only": False},
        )
    )
    steps_payload = _decode_tool_payload(steps_result)
    assert steps_payload["steps"][0]["step_id"] == "generate_primary_artifacts"
    assert steps_payload["steps"][0]["attempt_count"] == 1

    artifacts_result = asyncio.run(mcp_server.server.call_tool("list_task_artifacts", {"task_id": "task-observe"}))
    artifacts_payload = _decode_tool_payload(artifacts_result)
    assert artifacts_payload["artifacts"][0]["kind"] == "github_repository"


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


def test_schema_resources():
    execution_step = asyncio.run(
        mcp_server.server.read_resource("canvas-assignment-workflow://schemas/execution-step-v1")
    )
    execution_step_payload = _decode_resource_payload(execution_step)
    assert execution_step_payload["name"] == "execution_step_v1"
    assert "task_id" in execution_step_payload["properties"]

    scorecard = asyncio.run(
        mcp_server.server.read_resource("canvas-assignment-workflow://schemas/agent-scorecard-v1")
    )
    scorecard_payload = _decode_resource_payload(scorecard)
    assert scorecard_payload["name"] == "agent_scorecard_v1"
    assert "success_rate" in scorecard_payload["properties"]

    resume = asyncio.run(
        mcp_server.server.read_resource("canvas-assignment-workflow://schemas/resume-task-v1")
    )
    resume_payload = _decode_resource_payload(resume)
    assert resume_payload["name"] == "resume_task_v1"
    assert "step_ids" in resume_payload["properties"]

    inspection = asyncio.run(
        mcp_server.server.read_resource("canvas-assignment-workflow://schemas/delegation-tool-inspection-v1")
    )
    inspection_payload = _decode_resource_payload(inspection)
    assert inspection_payload["name"] == "delegation_tool_inspection_v1"
    assert "tool_selection" in inspection_payload["properties"]


def test_list_task_steps_tool_supports_filters():
    api.TASK_STORE.clear()
    api.TASK_STORE["task-filter"] = api._build_task_status(
        task_id="task-filter",
        request={"course_id": 123},
        status="completed",
        submitted_at="2026-03-20T00:00:00Z",
    )
    api._save_task_step(
        "task-filter",
        api._build_task_step(
            task_id="task-filter",
            step_id="execute_generated_project",
            title="Execute generated project",
            position=2,
            mode="delegated",
            capability_family="execution",
            status="blocked",
            started_at="2026-03-20T00:00:00Z",
            failed_at="2026-03-20T00:00:01Z",
        ),
    )
    api._save_task_step(
        "task-filter",
        api._build_task_step(
            task_id="task-filter",
            step_id="execute_generated_project",
            title="Execute generated project",
            position=2,
            mode="delegated",
            capability_family="execution",
            status="running",
            started_at="2026-03-20T00:00:02Z",
        ),
    )

    result = asyncio.run(
        mcp_server.server.call_tool(
            "list_task_steps",
            {
                "task_id": "task-filter",
                "status": "running",
                "retried_only": True,
                "delegated_only": True,
            },
        )
    )

    payload = _decode_tool_payload(result)
    assert len(payload["steps"]) == 1
    assert payload["steps"][0]["retry_count"] == 1


def test_smithery_execution_pilot_resource():
    result = asyncio.run(
        mcp_server.server.read_resource("canvas-assignment-workflow://profiles/smithery-execution-pilot")
    )

    payload = _decode_resource_payload(result)
    assert payload["profile_id"] == "smithery-execution-pilot"
    assert payload["delegation_env"]["DELEGATION_MIN_TRUST_LEVEL"] == "verified_profile"