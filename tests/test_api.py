from fastapi.testclient import TestClient

import api


class StubCanvasTools:
    async def list_courses(self):
        return [{"id": 1, "name": "Course One"}]

    async def get_course_assignments(self, course_id):
        return [{"id": 42, "name": f"Assignment for {course_id}"}]


class StubAgentSuccess:
    async def run(self, **kwargs):
        return {
            "destination": "github",
            "repository": {"html_url": "https://example.com/repo"},
            "request": kwargs,
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


def test_get_courses_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)

    client = TestClient(api.app)
    response = client.get("/courses")

    assert response.status_code == 200
    assert response.json() == {"courses": [{"id": 1, "name": "Course One"}]}


def test_get_assignments_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasTools)

    client = TestClient(api.app)
    response = client.get("/courses/123/assignments")

    assert response.status_code == 200
    assert response.json() == {
        "assignments": [{"id": 42, "name": "Assignment for 123"}]
    }


def test_create_success(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentSuccess)

    client = TestClient(api.app)
    response = client.post(
        "/create",
        json={
            "course_id": 123,
            "assignment_id": 777,
            "language": "python",
            "assignment_type": "coding",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["destination"] == "github"
    assert payload["repository"]["html_url"] == "https://example.com/repo"
    assert payload["request"]["course_id"] == 123


def test_create_returns_400_when_agent_returns_none(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentNone)

    client = TestClient(api.app)
    response = client.post(
        "/create",
        json={"course_id": 123, "language": "python"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Agent failed to create destination."


def test_get_courses_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasToolsError)

    client = TestClient(api.app)
    response = client.get("/courses")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch courses."


def test_get_assignments_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasTools", StubCanvasToolsError)

    client = TestClient(api.app)
    response = client.get("/courses/123/assignments")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch assignments."


def test_create_sanitizes_internal_errors(monkeypatch):
    monkeypatch.setattr(api, "CanvasGitHubAgent", StubAgentError)

    client = TestClient(api.app)
    response = client.post(
        "/create",
        json={"course_id": 123, "language": "python"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create destination."
