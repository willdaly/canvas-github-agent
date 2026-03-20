from subprocess import CompletedProcess

import pytest

from app.remote_agents import DelegationError, SmitheryRemoteAgentClient


def test_remote_agent_client_normalizes_plain_text_output(monkeypatch):
    client = SmitheryRemoteAgentClient(smithery_command="smithery")

    monkeypatch.setattr(client, "_ensure_connection", lambda connection_id, connection_url: connection_id)
    monkeypatch.setattr(
        client,
        "resolve_tool_name",
        lambda **kwargs: (kwargs["requested_tool_name"], {"inputSchema": {"type": "object"}}),
    )
    monkeypatch.setattr(client, "_call_tool", lambda connection_id, tool_name, args: {"raw_output": "ok"})

    result = __import__("asyncio").run(
        client.evaluate_assignment_output(
            candidate={
                "agent_id": "stub-evaluation-agent",
                "name": "Stub Evaluation Agent",
                "source": "test",
                "protocols": ["mcp"],
                "invocation": {"connection_url": None},
            },
            payload={"assignment": {"name": "Homework 1"}, "artifacts": []},
            connection_id="stub-evaluation-agent",
        )
    )

    assert result["status"] == "completed"
    assert result["validation"]["response"]["raw_output"] == "ok"


def test_remote_agent_client_normalizes_execution_output(monkeypatch):
    client = SmitheryRemoteAgentClient(smithery_command="smithery")

    monkeypatch.setattr(client, "_ensure_connection", lambda connection_id, connection_url: connection_id)
    monkeypatch.setattr(
        client,
        "resolve_tool_name",
        lambda **kwargs: (kwargs["requested_tool_name"], {"inputSchema": {"type": "object"}}),
    )
    monkeypatch.setattr(client, "_call_tool", lambda connection_id, tool_name, args: {"tests_passed": True})

    result = __import__("asyncio").run(
        client.execute_assignment_output(
            candidate={
                "agent_id": "stub-execution-agent",
                "name": "Stub Execution Agent",
                "source": "test",
                "protocols": ["mcp"],
                "invocation": {"connection_url": None},
            },
            payload={"assignment": {"name": "Homework 1"}, "artifacts": []},
            connection_id="stub-execution-agent",
        )
    )

    assert result["status"] == "completed"
    assert result["execution"]["response"]["tests_passed"] is True


def test_resolve_tool_name_uses_schema_compatible_match(monkeypatch):
    client = SmitheryRemoteAgentClient(smithery_command="smithery")

    def _run(args):
        if args[:3] == ["tool", "find", "conn"]:
            return CompletedProcess(args=args, returncode=0, stdout='{"tools":[{"name":"runner.execute"}]}', stderr="")
        if args[:3] == ["tool", "get", "conn"]:
            return CompletedProcess(
                args=args,
                returncode=0,
                stdout='{"inputSchema":{"type":"object","properties":{"assignment":{},"artifacts":{}}}}',
                stderr="",
            )
        raise AssertionError(args)

    monkeypatch.setattr(client, "_run", _run)

    tool_name, schema = client.resolve_tool_name(
        connection_id="conn",
        requested_tool_name="execute",
        payload={"assignment": {"name": "Homework 1"}, "artifacts": []},
        intent_queries=["execute assignment"],
    )

    assert tool_name == "runner.execute"
    assert schema["inputSchema"]["type"] == "object"


def test_resolve_tool_name_raises_for_incompatible_requested_tool(monkeypatch):
    client = SmitheryRemoteAgentClient(smithery_command="smithery")

    def _run(args):
        if args[:3] == ["tool", "find", "conn"]:
            return CompletedProcess(args=args, returncode=0, stdout='{"tools":[{"name":"runner.execute"}]}', stderr="")
        if args[:3] == ["tool", "get", "conn"]:
            return CompletedProcess(
                args=args,
                returncode=0,
                stdout='{"inputSchema":{"type":"object","properties":{"repo":{},"command":{}}}}',
                stderr="",
            )
        raise AssertionError(args)

    monkeypatch.setattr(client, "_run", _run)

    with pytest.raises(DelegationError, match="No compatible schema found"):
        client.resolve_tool_name(
            connection_id="conn",
            requested_tool_name="runner.execute",
            payload={"assignment": {"name": "Homework 1"}, "artifacts": []},
            intent_queries=["execute assignment"],
        )


def test_inspect_assignment_tool_ensures_connection(monkeypatch):
    client = SmitheryRemoteAgentClient(smithery_command="smithery")
    ensure_calls = []

    monkeypatch.setattr(
        client,
        "_ensure_connection",
        lambda connection_id, connection_url: ensure_calls.append((connection_id, connection_url)) or connection_id,
    )
    monkeypatch.setattr(
        client,
        "resolve_tool_name",
        lambda **kwargs: ("runner.execute", {"inputSchema": {"type": "object"}}),
    )

    result = __import__("asyncio").run(
        client.inspect_assignment_tool(
            connection_id="conn",
            connection_url="https://example.com/mcp",
            requested_tool_name="execute",
            payload={"assignment": {"name": "Homework 1"}, "artifacts": []},
            intent_queries=["execute assignment"],
        )
    )

    assert ensure_calls == [("conn", "https://example.com/mcp")]
    assert result["tool_name"] == "runner.execute"