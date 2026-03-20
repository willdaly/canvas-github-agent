import asyncio

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


class StubCanvasToolsError:
    async def list_courses(self):
        raise RuntimeError("sensitive canvas token leak")

    async def get_course_assignments(self, course_id):
        raise RuntimeError("sensitive assignment query failure")


class StubAgentError:
    async def run(self, **kwargs):
        raise RuntimeError("sensitive github failure")


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
    assert payload["result_schema"]["name"] == "task_result_v1"
    assert payload["operations"][0]["name"] == "list_courses"


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


def test_create_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentError)
    response = asyncio.run(_request("POST", "/create", {"course_id": 123, "language": "python"}))

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create destination."
