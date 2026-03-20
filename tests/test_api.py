import asyncio
from uuid import UUID

from httpx import ASGITransport, AsyncClient

import api


async def _request(method, url, payload=None):
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, url, json=payload)


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
                "module_name": f"Module for {course_id}",
                "section_title": "Bayes Review",
                "item_type": "Page",
                "distance": 0.5,
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


class StubWritingAgentSuccess:
    async def run(self, **kwargs):
        return {
            "destination": "notion",
            "assignment": {
                "id": kwargs.get("assignment_id") or 555,
                "name": "Essay Draft",
                "due_at": "2026-03-31T12:00:00Z",
                "workflow_state": "unsubmitted",
                "is_completed": False,
            },
            "page": {"id": "page_123", "url": "https://notion.so/page_123"},
        }


class StubAgentNone:
    async def run(self, **kwargs):
        return None

    async def fetch_assignment(self, course_id, assignment_id=None):
        return None


class StubCanvasToolsError:
    async def list_courses(self):
        raise RuntimeError("sensitive canvas token leak")

    async def get_course_assignments(self, course_id):
        raise RuntimeError("sensitive assignment query failure")

    async def get_course_modules(self, course_id):
        raise RuntimeError("sensitive module listing failure")

    async def search_course_module_context(self, course_id, query, limit):
        raise RuntimeError("sensitive module search failure")


class StubAgentError:
    async def run(self, **kwargs):
        raise RuntimeError("sensitive github failure")

    async def fetch_assignment(self, course_id, assignment_id=None):
        raise RuntimeError("sensitive planning failure")


class StubTaskScheduler:
    def __init__(self):
        self.calls = []

    def __call__(self, task_id, req):
        self.calls.append((task_id, req))


class StubResumeScheduler:
    def __init__(self):
        self.calls = []

    def __call__(self, task_id, req, step_ids, force_full_rerun=False):
        self.calls.append((task_id, req, step_ids, force_full_rerun))


class StubCourseContextTools:
    def ingest_pdf(self, course_id, file_path, document_name=None):
        return {
            "status": "ingested",
            "course_id": course_id,
            "document_id": "slides",
            "document_name": document_name or "slides.pdf",
            "chunk_count": 3,
            "collection": "course-context",
            "storage_path": ".chroma",
        }

    def list_documents(self, course_id):
        return [
            {
                "course_id": course_id,
                "document_id": "slides",
                "document_name": "slides.pdf",
                "source_path": "docs/slides.pdf",
                "chunk_count": 3,
            }
        ]

    def search_context(self, course_id, query, limit):
        return [
            {
                "id": "course-123:slides:0000",
                "course_id": course_id,
                "document_id": "slides",
                "document_name": "slides.pdf",
                "section_title": "Bayes Review",
                "chunk_index": 0,
                "distance": 0.1234,
                "text": "Section: Bayes Review\n\nPosterior is proportional to prior times likelihood.",
            }
        ][:limit]


class StubCourseContextToolsFileMissing:
    def ingest_pdf(self, course_id, file_path, document_name=None):
        raise FileNotFoundError(file_path)


class StubCourseContextToolsError:
    def list_documents(self, course_id):
        raise RuntimeError("course context not configured")

    def search_context(self, course_id, query, limit):
        raise RuntimeError("course context not configured")


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
            "execution": {
                "status": "completed",
                "response": {
                    "tests_passed": True,
                    "benchmarks_completed": True,
                },
            },
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
            "validation": {
                "status": "completed",
                "response": {
                    "score": 0.91,
                    "summary": "Assignment output aligns with the requested maze scaffold.",
                },
            },
            "errors": None,
            "timing": {
                "started_at": "2026-03-20T00:00:00Z",
                "completed_at": "2026-03-20T00:00:01Z",
            },
        }


def test_get_oasf_record_success(monkeypatch):
    monkeypatch.setattr(
        api,
        "build_service_oasf_record",
        lambda *args, **kwargs: {"name": "Canvas Assignment Workflow", "schema_version": "1.0.0"},
    )
    response = asyncio.run(_request("GET", "/metadata/oasf-record"))

    assert response.status_code == 200
    assert response.json() == {
        "name": "Canvas Assignment Workflow",
        "schema_version": "1.0.0",
    }


def test_get_health_success():
    response = asyncio.run(_request("GET", "/health"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "canvas-assignment-workflow",
        "version": "0.1.0",
    }


def test_get_capabilities_success(monkeypatch):
    monkeypatch.setattr(api, "get_service_base_url", lambda: "https://agent.example.com")
    response = asyncio.run(_request("GET", "/capabilities"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"]["base_url"] == "https://agent.example.com"
    assert payload["transports"]["mcp_stdio"]["command"] == "canvas-github-agent-mcp"
    assert payload["discovery_schema"]["name"] == "agent_candidate_v1"
    assert payload["planning_schema"]["name"] == "assignment_plan_v1"
    assert payload["result_schema"]["name"] == "task_result_v1"
    assert payload["task_schema"]["name"] == "task_status_v1"
    assert payload["task_step_schema"]["name"] == "execution_step_v1"
    assert "canvas-assignment-workflow://schemas/delegation-tool-inspection-v1" in payload["transports"]["mcp_stdio"]["resources"]
    assert payload["operations"][0]["name"] == "list_courses"


def test_discover_agents_success(monkeypatch):
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())

    response = asyncio.run(
        _request(
            "POST",
            "/discover-agents",
            {
                "capability_family": "evaluation",
                "limit": 1,
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["query"]["capability_family"] == "evaluation"
    assert payload["candidates"][0]["name"] == "Stub Evaluation Agent"
    assert payload["candidates"][0]["ranking_explanation"]["summary"]


def test_discover_agents_includes_scorecard_ranking_explanation(monkeypatch):
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    api.TASK_STORE.clear()
    for _ in range(3):
        api.TASK_STORE.record_agent_scorecard_event(
            agent_id="stub-execution-agent",
            capability_family="execution",
            status="completed",
            tool_name="runner.execute",
            task_id="task-1",
            step_id="execute_generated_project",
        )

    response = asyncio.run(
        _request(
            "POST",
            "/discover-agents",
            {
                "capability_family": "execution",
                "limit": 1,
            },
        )
    )

    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["scorecard"]["success_rate"] == 1.0
    assert candidate["ranking_explanation"]["scorecard_applied"] is True
    assert candidate["ranking_explanation"]["scorecard_bonus"] > 0


def test_discover_agents_sanitizes_internal_errors(monkeypatch):
    class ExplodingRegistry:
        def discover_agents(self, **kwargs):
            raise RuntimeError("sensitive discovery failure")

    monkeypatch.setattr(api, "AGENT_REGISTRY", ExplodingRegistry())

    response = asyncio.run(
        _request(
            "POST",
            "/discover-agents",
            {
                "capability_family": "evaluation",
                "limit": 1,
            },
        )
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to discover agents."


def test_create_with_delegated_evaluation_attaches_provenance(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())

    response = asyncio.run(
        _request(
            "POST",
            "/create",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "enable_delegated_evaluation": True,
                "evaluation_agent_id": "stub-evaluation-agent",
                "evaluation_connection_id": "stub-evaluation-agent",
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["details"]["delegated_evaluation"]["status"] == "completed"
    assert payload["details"]["delegated_evaluation"]["validation"]["response"]["score"] == 0.91
    assert payload["details"]["artifact_provenance"][-1]["kind"] == "delegated_evaluation"
    assert payload["details"]["artifact_provenance"][0]["validation_status"] == "validated"


def test_create_with_delegated_execution_attaches_provenance(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())

    response = asyncio.run(
        _request(
            "POST",
            "/create",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "enable_delegated_execution": True,
                "execution_agent_id": "stub-execution-agent",
                "execution_connection_id": "stub-execution-agent",
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["details"]["delegated_execution"]["status"] == "completed"
    assert payload["details"]["delegated_execution"]["execution"]["response"]["tests_passed"] is True
    assert payload["details"]["artifact_provenance"][-1]["kind"] == "delegated_execution"


def test_create_blocks_unlisted_delegation_without_explicit_target(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())

    response = asyncio.run(
        _request(
            "POST",
            "/create",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "enable_delegated_execution": True,
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["details"]["delegated_execution"]["status"] == "blocked"
    assert payload["details"]["delegation_policy"]["execution"]["allowed"] is False


def test_create_blocks_delegation_when_scorecard_threshold_fails(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())

    api.TASK_STORE.clear()
    api.TASK_STORE.record_agent_scorecard_event(
        agent_id="stub-execution-agent",
        capability_family="execution",
        status="failed",
        tool_name="runner.execute",
        task_id="task-1",
        step_id="execute_generated_project",
    )

    monkeypatch.setenv("DELEGATION_ENFORCE_SCORECARD_THRESHOLDS", "true")
    monkeypatch.setenv("DELEGATION_MIN_SCORECARD_SUCCESS_RATE", "0.8")
    monkeypatch.setenv("DELEGATION_MIN_SCORECARD_TOTAL_COUNT", "1")

    response = asyncio.run(
        _request(
            "POST",
            "/create",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "enable_delegated_execution": True,
                "execution_agent_id": "stub-execution-agent",
                "execution_connection_id": "stub-execution-agent",
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["details"]["delegated_execution"]["status"] == "blocked"
    assert payload["details"]["delegation_policy"]["execution"]["basis"] == "scorecard_threshold"
    assert payload["details"]["delegation_policy"]["execution"]["scorecard"]["success_rate"] == 0.0


def test_plan_assignment_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())

    response = asyncio.run(
        _request(
            "POST",
            "/plan",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "planned"
    assert payload["assignment"]["name"] == "Homework 1"
    assert payload["plan"]["domain"] == "maze_search"
    assert payload["plan"]["subtasks"][0]["id"] == "retrieve_context"
    assert payload["plan"]["delegation_candidates"][0]["capability"] == "evaluation"
    assert payload["plan"]["delegation_candidates"][0]["candidates"][0]["name"] == "Stub Evaluation Agent"
    assert payload["confidence"] >= 0.55


def test_plan_assignment_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentError)

    response = asyncio.run(
        _request(
            "POST",
            "/plan",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
            },
        )
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to plan assignment."


def test_submit_task_returns_queued_task(monkeypatch):
    api.TASK_STORE.clear()
    scheduler = StubTaskScheduler()
    monkeypatch.setattr(api, "_schedule_task_execution", scheduler)

    response = asyncio.run(
        _request(
            "POST",
            "/tasks",
            {
                "course_id": 123,
                "assignment_id": 777,
                "language": "python",
                "assignment_type": "coding",
            },
        )
    )

    assert response.status_code == 202
    payload = response.json()
    UUID(payload["task_id"])
    assert payload["status"] == "queued"
    assert payload["request"]["course_id"] == 123
    assert payload["result"] is None
    assert payload["error"] is None
    assert len(scheduler.calls) == 1


def test_resume_task_queues_selected_step_retry(monkeypatch):
    api.TASK_STORE.clear()
    scheduler = StubResumeScheduler()
    monkeypatch.setattr(api, "_schedule_task_resume", scheduler)
    req = api.CreateRequest(
        course_id=123,
        assignment_id=777,
        language="python",
        enable_delegated_execution=True,
        execution_agent_id="stub-execution-agent",
        execution_connection_id="stub-execution-agent",
    )
    api.TASK_STORE["task-resume"] = api._build_task_status(
        task_id="task-resume",
        request=api._request_payload(req),
        status="completed",
        submitted_at="2026-03-20T00:00:00Z",
        completed_at="2026-03-20T00:00:01Z",
        result={
            "status": "completed",
            "service": {"name": "Canvas Assignment Workflow", "slug": "canvas-assignment-workflow", "version": "0.1.0"},
            "request": api._request_payload(req),
            "route": {"destination": "github", "assignment_type": "coding", "language": "python", "notion_content_mode": None},
            "assignment": {"id": 777, "name": "Homework 1"},
            "artifacts": [{"kind": "github_repository", "url": "https://example.com/repo"}],
            "details": {"delegated_execution": {"status": "blocked"}},
        },
    )
    api.TASK_STORE.save_step(
        "task-resume",
        {
            "task_id": "task-resume",
            "step_id": "execute_generated_project",
            "title": "Execute generated project",
            "position": 2,
            "mode": "delegated",
            "capability_family": "execution",
            "status": "blocked",
            "started_at": "2026-03-20T00:00:00Z",
            "completed_at": None,
            "failed_at": "2026-03-20T00:00:01Z",
            "agent": {"agent_id": "stub-execution-agent", "name": "Stub Execution Agent"},
            "policy": {"allowed": False},
            "summary": None,
            "result": None,
            "error": {"message": "blocked"},
        },
    )

    response = asyncio.run(
        _request(
            "POST",
            "/tasks/task-resume/resume",
            {"step_ids": ["execute_generated_project"]},
        )
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert scheduler.calls[0][2] == ["execute_generated_project"]
    assert scheduler.calls[0][3] is False


def test_save_task_step_tracks_retry_metadata():
    api.TASK_STORE.clear()
    api.TASK_STORE["task-retry"] = api._build_task_status(
        task_id="task-retry",
        request={"course_id": 123},
        status="queued",
        submitted_at="2026-03-20T00:00:00Z",
    )

    api._save_task_step(
        "task-retry",
        api._build_task_step(
            task_id="task-retry",
            step_id="execute_generated_project",
            title="Execute generated project",
            position=2,
            mode="delegated",
            capability_family="execution",
            status="blocked",
            started_at="2026-03-20T00:00:00Z",
            failed_at="2026-03-20T00:00:01Z",
            error={"message": "blocked"},
        ),
    )
    api._save_task_step(
        "task-retry",
        api._build_task_step(
            task_id="task-retry",
            step_id="execute_generated_project",
            title="Execute generated project",
            position=2,
            mode="delegated",
            capability_family="execution",
            status="running",
            started_at="2026-03-20T00:00:02Z",
        ),
    )

    step = api.TASK_STORE.get_step("task-retry", "execute_generated_project")
    assert step is not None
    assert step["attempt_count"] == 2
    assert step["retry_count"] == 1
    assert step["last_retry_at"] == "2026-03-20T00:00:02Z"
    assert step["retry_history"][0]["status"] == "blocked"


def test_inspect_task_delegation_tool_success(monkeypatch):
    api.TASK_STORE.clear()
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())

    class InspectingRemoteAgentClient(StubRemoteAgentClient):
        async def inspect_assignment_tool(self, **kwargs):
            return {
                "tool_name": "runner.execute",
                "schema": {"inputSchema": {"type": "object"}},
                "connection_id": kwargs["connection_id"],
                "connection_url": kwargs["connection_url"],
            }

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

    response = asyncio.run(
        _request(
            "POST",
            "/tasks/task-inspect/inspect-delegation-tool",
            {"capability_family": "execution"},
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["tool_selection"]["tool_name"] == "runner.execute"
    assert payload["policy"]["allowed"] is True


def test_get_task_steps_supports_status_retry_and_mode_filters():
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
            step_id="generate_primary_artifacts",
            title="Generate primary artifacts",
            position=1,
            mode="local",
            status="completed",
            started_at="2026-03-20T00:00:00Z",
            completed_at="2026-03-20T00:00:01Z",
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
            status="blocked",
            started_at="2026-03-20T00:00:02Z",
            failed_at="2026-03-20T00:00:03Z",
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
            started_at="2026-03-20T00:00:04Z",
        ),
    )

    response = asyncio.run(
        _request(
            "GET",
            "/tasks/task-filter/steps?status=running&retried_only=true&delegated_only=true",
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"]["retried_only"] is True
    assert payload["filters"]["delegated_only"] is True
    assert len(payload["steps"]) == 1
    assert payload["steps"][0]["step_id"] == "execute_generated_project"

def test_execute_task_persists_tool_selection_in_step_summary(monkeypatch):
    api.TASK_STORE.clear()
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())
    req = api.CreateRequest(
        course_id=123,
        assignment_id=777,
        language="python",
        enable_delegated_execution=True,
        execution_agent_id="stub-execution-agent",
        execution_connection_id="stub-execution-agent",
    )
    api.TASK_STORE["task-tool-selection"] = api._build_task_status(
        task_id="task-tool-selection",
        request=api._request_payload(req),
        status="queued",
        submitted_at="2026-03-20T00:00:00Z",
    )

    asyncio.run(api._execute_task("task-tool-selection", req))

    step = api.TASK_STORE.get_step("task-tool-selection", "execute_generated_project")
    assert step is not None
    assert step["summary"]["tool_selection"] is not None
    assert step["summary"]["tool_selection"]["tool_name"] == "execute"


def test_resume_task_rejects_running_task():
    api.TASK_STORE.clear()
    api.TASK_STORE["task-running"] = api._build_task_status(
        task_id="task-running",
        request={"course_id": 123},
        status="running",
        submitted_at="2026-03-20T00:00:00Z",
    )

    response = asyncio.run(_request("POST", "/tasks/task-running/resume", {}))

    assert response.status_code == 409
    assert response.json()["detail"] == "Task is already queued or running."


def test_ingest_course_document_success(monkeypatch):
    monkeypatch.setattr(api, "CourseContextTools", StubCourseContextTools)

    response = asyncio.run(
        _request(
            "POST",
            "/courses/123/documents/ingest",
            {"file_path": "docs/slides.pdf", "document_name": "AAI Slides"},
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ingested"
    assert payload["course_id"] == 123
    assert payload["document_name"] == "AAI Slides"


def test_ingest_course_document_returns_404_for_missing_file(monkeypatch):
    monkeypatch.setattr(api, "CourseContextTools", StubCourseContextToolsFileMissing)

    response = asyncio.run(
        _request(
            "POST",
            "/courses/123/documents/ingest",
            {"file_path": "docs/missing.pdf"},
        )
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Course document not found."


def test_get_course_documents_success(monkeypatch):
    monkeypatch.setattr(api, "CourseContextTools", StubCourseContextTools)

    response = asyncio.run(_request("GET", "/courses/123/documents"))

    assert response.status_code == 200
    assert response.json()["documents"][0]["document_name"] == "slides.pdf"


def test_search_course_context_success(monkeypatch):
    monkeypatch.setattr(api, "CourseContextTools", StubCourseContextTools)

    response = asyncio.run(
        _request(
            "POST",
            "/courses/123/context/search",
            {"query": "posterior update", "limit": 1},
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["course_id"] == 123
    assert payload["results"][0]["section_title"] == "Bayes Review"


def test_search_course_context_sanitizes_runtime_errors(monkeypatch):
    monkeypatch.setattr(api, "CourseContextTools", StubCourseContextToolsError)

    response = asyncio.run(
        _request(
            "POST",
            "/courses/123/context/search",
            {"query": "posterior update", "limit": 1},
        )
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "course context not configured"


def test_get_task_returns_existing_task():
    api.TASK_STORE.clear()
    api.TASK_STORE["task-123"] = {
        "task_id": "task-123",
        "status": "queued",
        "service": {
            "name": "Canvas Assignment Workflow",
            "slug": "canvas-assignment-workflow",
            "version": "0.1.0",
        },
        "request": {
            "course_id": 123,
            "assignment_id": 777,
            "language": "python",
            "assignment_type": "coding",
            "notion_content_mode": None,
            "enable_delegated_evaluation": False,
            "evaluation_agent_id": None,
            "evaluation_connection_id": None,
            "evaluation_connection_url": None,
            "evaluation_tool_name": "evaluate",
            "evaluation_include_live_results": False,
            "enable_delegated_execution": False,
            "execution_agent_id": None,
            "execution_connection_id": None,
            "execution_connection_url": None,
            "execution_tool_name": "execute",
            "execution_include_live_results": False,
        },
        "submitted_at": "2026-03-20T00:00:00Z",
        "started_at": None,
        "completed_at": None,
        "failed_at": None,
        "result": None,
        "error": None,
    }

    response = asyncio.run(_request("GET", "/tasks/task-123"))

    assert response.status_code == 200
    assert response.json()["task_id"] == "task-123"


def test_get_task_returns_404_for_unknown_task():
    api.TASK_STORE.clear()
    response = asyncio.run(_request("GET", "/tasks/missing-task"))

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found."


def test_get_task_steps_returns_persisted_steps():
    api.TASK_STORE.clear()
    api.TASK_STORE["task-steps"] = api._build_task_status(
        task_id="task-steps",
        request={"course_id": 123},
        status="completed",
        submitted_at="2026-03-20T00:00:00Z",
    )
    api.TASK_STORE.save_step(
        "task-steps",
        {
            "task_id": "task-steps",
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

    response = asyncio.run(_request("GET", "/tasks/task-steps/steps"))

    assert response.status_code == 200
    assert response.json()["steps"][0]["step_id"] == "generate_primary_artifacts"


def test_get_task_artifacts_returns_provenance():
    api.TASK_STORE.clear()
    api.TASK_STORE["task-artifacts"] = api._build_task_status(
        task_id="task-artifacts",
        request={"course_id": 123},
        status="completed",
        submitted_at="2026-03-20T00:00:00Z",
        result={
            "artifacts": [{"kind": "github_repository", "url": "https://example.com/repo"}],
            "details": {
                "artifact_provenance": [{"artifact_id": "artifact-1:github_repository", "kind": "github_repository"}]
            },
        },
    )

    response = asyncio.run(_request("GET", "/tasks/task-artifacts/artifacts"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifacts"][0]["kind"] == "github_repository"
    assert payload["provenance"][0]["artifact_id"] == "artifact-1:github_repository"


def test_list_agent_scorecards_returns_persisted_rows():
    api.TASK_STORE.clear()
    api.TASK_STORE.record_agent_scorecard_event(
        agent_id="stub-evaluation-agent",
        capability_family="evaluation",
        status="completed",
        tool_name="grader.evaluate",
        task_id="task-1",
        step_id="validate_generated_project",
    )

    response = asyncio.run(_request("GET", "/agents/scorecards"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["scorecards"][0]["agent_id"] == "stub-evaluation-agent"
    assert payload["scorecards"][0]["success_rate"] == 1.0


def test_get_oasf_record_sanitizes_internal_errors(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("sensitive oasf generation failure")

    monkeypatch.setattr(api, "build_service_oasf_record", _raise)
    response = asyncio.run(_request("GET", "/metadata/oasf-record"))

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to build OASF record."


def test_get_courses_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)
    response = asyncio.run(_request("GET", "/courses"))

    assert response.status_code == 200
    assert response.json() == {"courses": [{"id": 1, "name": "Course One"}]}


def test_get_assignments_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)
    response = asyncio.run(_request("GET", "/courses/123/assignments"))

    assert response.status_code == 200
    assert response.json() == {
        "assignments": [{"id": 42, "name": "Assignment for 123"}]
    }


def test_get_modules_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)
    response = asyncio.run(_request("GET", "/courses/123/modules"))

    assert response.status_code == 200
    assert response.json()["modules"][0]["name"] == "Module for 123"


def test_search_course_modules_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)
    response = asyncio.run(
        _request(
            "POST",
            "/courses/123/modules/search",
            {"query": "posterior update", "limit": 1},
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["course_id"] == 123
    assert payload["results"][0]["section_title"] == "Bayes Review"


def test_create_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    response = asyncio.run(
        _request(
            "POST",
            "/create",
            {
            "course_id": 123,
            "assignment_id": 777,
            "language": "python",
            "assignment_type": "coding",
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["service"]["slug"] == "canvas-assignment-workflow"
    assert payload["route"]["destination"] == "github"
    assert payload["route"]["assignment_type"] == "coding"
    assert payload["artifacts"][0]["url"] == "https://example.com/repo"
    assert payload["request"]["course_id"] == 123
    assert payload["assignment"]["name"] == "Homework 1"
    assert payload["details"]["files_uploaded"] is True


def test_create_passes_notion_content_mode(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubWritingAgentSuccess)
    response = asyncio.run(
        _request(
            "POST",
            "/create",
            {
                "course_id": 123,
                "assignment_type": "writing",
                "notion_content_mode": "text",
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request"]["notion_content_mode"] == "text"
    assert payload["route"]["destination"] == "notion"
    assert payload["route"]["assignment_type"] == "writing"
    assert payload["route"]["notion_content_mode"] == "text"
    assert payload["artifacts"][0]["kind"] == "notion_page"


def test_create_returns_400_when_agent_returns_none(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentNone)
    response = asyncio.run(_request("POST", "/create", {"course_id": 123, "language": "python"}))

    assert response.status_code == 400
    assert response.json()["detail"] == "Agent failed to create destination."


def test_get_courses_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasToolsError)
    response = asyncio.run(_request("GET", "/courses"))

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch courses."


def test_get_assignments_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasToolsError)
    response = asyncio.run(_request("GET", "/courses/123/assignments"))

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch assignments."


def test_get_modules_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasToolsError)
    response = asyncio.run(_request("GET", "/courses/123/modules"))

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch modules."


def test_search_course_modules_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasToolsError)
    response = asyncio.run(
        _request(
            "POST",
            "/courses/123/modules/search",
            {"query": "posterior update", "limit": 1},
        )
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to search course modules."


def test_create_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentError)
    response = asyncio.run(_request("POST", "/create", {"course_id": 123, "language": "python"}))

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create destination."


def test_execute_task_completes_successfully(monkeypatch):
    api.TASK_STORE.clear()
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    req = api.CreateRequest(
        course_id=123,
        assignment_id=777,
        language="python",
        assignment_type="coding",
    )
    api.TASK_STORE["task-success"] = api._build_task_status(
        task_id="task-success",
        request=api._request_payload(req),
        status="queued",
        submitted_at="2026-03-20T00:00:00Z",
    )

    asyncio.run(api._execute_task("task-success", req))

    task = api.TASK_STORE["task-success"]
    assert task["status"] == "completed"
    assert task["result"]["route"]["destination"] == "github"
    assert task["completed_at"] is not None
    assert api.TASK_STORE.list_steps("task-success")[0]["status"] == "completed"


def test_execute_task_marks_failure_when_agent_returns_none(monkeypatch):
    api.TASK_STORE.clear()
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentNone)
    req = api.CreateRequest(course_id=123, language="python")
    api.TASK_STORE["task-none"] = api._build_task_status(
        task_id="task-none",
        request=api._request_payload(req),
        status="queued",
        submitted_at="2026-03-20T00:00:00Z",
    )

    asyncio.run(api._execute_task("task-none", req))

    task = api.TASK_STORE["task-none"]
    assert task["status"] == "failed"
    assert task["error"]["code"] == "destination_creation_failed"


def test_execute_task_marks_failure_on_internal_error(monkeypatch):
    api.TASK_STORE.clear()
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentError)
    req = api.CreateRequest(course_id=123, language="python")
    api.TASK_STORE["task-error"] = api._build_task_status(
        task_id="task-error",
        request=api._request_payload(req),
        status="queued",
        submitted_at="2026-03-20T00:00:00Z",
    )

    asyncio.run(api._execute_task("task-error", req))

    task = api.TASK_STORE["task-error"]
    assert task["status"] == "failed"
    assert task["error"]["code"] == "internal_execution_error"


def test_execute_task_with_delegated_evaluation_persists_result(monkeypatch):
    api.TASK_STORE.clear()
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())
    req = api.CreateRequest(
        course_id=123,
        assignment_id=777,
        language="python",
        enable_delegated_evaluation=True,
        evaluation_agent_id="stub-evaluation-agent",
        evaluation_connection_id="stub-evaluation-agent",
    )
    api.TASK_STORE["task-eval"] = api._build_task_status(
        task_id="task-eval",
        request=api._request_payload(req),
        status="queued",
        submitted_at="2026-03-20T00:00:00Z",
    )

    asyncio.run(api._execute_task("task-eval", req))

    task = api.TASK_STORE["task-eval"]
    assert task["status"] == "completed"
    assert task["result"]["details"]["delegated_evaluation"]["status"] == "completed"


def test_execute_task_with_delegated_execution_persists_steps(monkeypatch):
    api.TASK_STORE.clear()
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)
    monkeypatch.setattr(api, "AGENT_REGISTRY", StubAgentRegistry())
    monkeypatch.setattr(api, "REMOTE_AGENT_CLIENT", StubRemoteAgentClient())
    req = api.CreateRequest(
        course_id=123,
        assignment_id=777,
        language="python",
        enable_delegated_execution=True,
        execution_agent_id="stub-execution-agent",
        execution_connection_id="stub-execution-agent",
    )
    api.TASK_STORE["task-exec"] = api._build_task_status(
        task_id="task-exec",
        request=api._request_payload(req),
        status="queued",
        submitted_at="2026-03-20T00:00:00Z",
    )

    asyncio.run(api._execute_task("task-exec", req))

    steps = api.TASK_STORE.list_steps("task-exec")
    assert steps[0]["step_id"] == "generate_primary_artifacts"
    assert steps[1]["step_id"] == "execute_generated_project"
    assert steps[1]["status"] == "completed"
    scorecards = api.TASK_STORE.list_agent_scorecards("execution")
    assert scorecards[0]["agent_id"] == "stub-execution-agent"
