"""Remote agent invocation helpers for delegated evaluation workflows."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class DelegationError(RuntimeError):
    """Raised when a delegated remote-agent step cannot be completed."""


class SmitheryRemoteAgentClient:
    """Invoke MCP tools through Smithery for optional delegated evaluation."""

    def __init__(self, smithery_command: Optional[str] = None):
        self.smithery_command = smithery_command or shutil.which("smithery")

    @staticmethod
    def _connection_id_from_name(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "remote-evaluation-agent"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        if not self.smithery_command:
            raise DelegationError("Smithery CLI is not installed.")
        return subprocess.run(
            [self.smithery_command, *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def _ensure_connection(self, connection_id: str, connection_url: Optional[str]) -> str:
        if not connection_url:
            return connection_id

        result = self._run(["mcp", "add", connection_url, "--id", connection_id])
        if result.returncode == 0:
            return connection_id

        combined_output = f"{result.stdout}\n{result.stderr}".lower()
        if "already exists" in combined_output or "connection already exists" in combined_output:
            return connection_id

        raise DelegationError("Failed to connect the remote evaluation agent through Smithery.")

    def _call_tool(self, connection_id: str, tool_name: str, args: dict[str, Any]) -> Any:
        result = self._run(["tool", "call", connection_id, tool_name, json.dumps(args)])
        if result.returncode != 0:
            raise DelegationError("Remote evaluation tool call failed.")

        output = result.stdout.strip()
        if not output:
            return {"raw_output": ""}

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"raw_output": output}

    @staticmethod
    def _parse_jsonish_output(output: str) -> Any:
        stripped = output.strip()
        if not stripped:
            return {}

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            lines = [line.strip() for line in stripped.splitlines() if line.strip()]
            parsed_lines: list[Any] = []
            for line in lines:
                try:
                    parsed_lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            if parsed_lines:
                return parsed_lines
            raise DelegationError("Smithery returned an unexpected non-JSON response.")

    def _find_tools(
        self,
        connection_id: str,
        query: str,
        *,
        match: str = "fuzzy",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        result = self._run(
            [
                "tool",
                "find",
                connection_id,
                query,
                "--match",
                match,
                "--limit",
                str(limit),
                "--json",
            ]
        )
        if result.returncode != 0:
            return []

        payload = self._parse_jsonish_output(result.stdout)
        if isinstance(payload, dict):
            tools = payload.get("tools") or payload.get("results") or payload.get("matches") or []
            if isinstance(tools, list):
                return [item for item in tools if isinstance(item, dict)]
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def _get_tool_schema(self, connection_id: str, tool_name: str) -> dict[str, Any]:
        result = self._run(["tool", "get", connection_id, tool_name])
        if result.returncode != 0:
            raise DelegationError(f"Failed to inspect schema for tool '{tool_name}'.")

        payload = self._parse_jsonish_output(result.stdout)
        if isinstance(payload, dict):
            return payload
        raise DelegationError(f"Invalid schema response for tool '{tool_name}'.")

    @staticmethod
    def _schema_accepts_payload(schema_payload: dict[str, Any], payload: dict[str, Any]) -> bool:
        input_schema = schema_payload.get("inputSchema") or schema_payload.get("input_schema") or schema_payload
        if not isinstance(input_schema, dict):
            return True

        schema_type = input_schema.get("type")
        if schema_type and schema_type != "object":
            return False

        properties = input_schema.get("properties")
        if not isinstance(properties, dict) or not properties:
            return True

        payload_keys = set(payload.keys())
        property_keys = set(properties.keys())
        if payload_keys & property_keys:
            return True

        required = input_schema.get("required")
        if isinstance(required, list) and not required:
            return True

        return False

    def resolve_tool_name(
        self,
        *,
        connection_id: str,
        requested_tool_name: str,
        payload: dict[str, Any],
        intent_queries: list[str],
    ) -> tuple[str, dict[str, Any]]:
        candidate_queries: list[str] = []
        if requested_tool_name and requested_tool_name.strip().lower() not in {"execute", "evaluate"}:
            candidate_queries.append(requested_tool_name.strip())
        candidate_queries.extend(query for query in intent_queries if query and query not in candidate_queries)

        attempted_tools: list[str] = []
        for query in candidate_queries:
            match_mode = "exact" if query == requested_tool_name and query.strip().lower() not in {"execute", "evaluate"} else "fuzzy"
            matches = self._find_tools(connection_id, query, match=match_mode, limit=10)
            for match in matches:
                tool_name = (
                    match.get("name")
                    or match.get("tool")
                    or match.get("qualifiedName")
                    or ""
                ).strip()
                if not tool_name or tool_name in attempted_tools:
                    continue
                attempted_tools.append(tool_name)
                schema = self._get_tool_schema(connection_id, tool_name)
                if self._schema_accepts_payload(schema, payload):
                    return tool_name, schema

        if requested_tool_name and requested_tool_name.strip().lower() not in {"execute", "evaluate"}:
            raise DelegationError(f"No compatible schema found for requested tool '{requested_tool_name}'.")
        raise DelegationError("No compatible remote tool could be resolved for the requested subtask.")

    async def inspect_assignment_tool(
        self,
        *,
        connection_id: str,
        connection_url: Optional[str] = None,
        requested_tool_name: str,
        payload: dict[str, Any],
        intent_queries: list[str],
    ) -> dict[str, Any]:
        """Resolve and return the schema for the remote tool that will be invoked."""
        await asyncio.to_thread(self._ensure_connection, connection_id, connection_url)
        tool_name, schema = await asyncio.to_thread(
            self.resolve_tool_name,
            connection_id=connection_id,
            requested_tool_name=requested_tool_name,
            payload=payload,
            intent_queries=intent_queries,
        )
        return {
            "tool_name": tool_name,
            "schema": schema,
            "connection_id": connection_id,
            "connection_url": connection_url,
        }

    async def _invoke_assignment_subtask(
        self,
        *,
        candidate: dict[str, Any],
        payload: dict[str, Any],
        connection_id: Optional[str] = None,
        connection_url: Optional[str] = None,
        tool_name: str,
        subtask_id: str,
        outcome_field: str,
    ) -> dict[str, Any]:
        """Run a delegated remote subtask and normalize the result."""
        started_at = _utcnow_iso()
        resolved_connection_id = connection_id or self._connection_id_from_name(
            candidate.get("agent_id") or candidate.get("name") or "remote-evaluation-agent"
        )
        resolved_connection_url = connection_url or candidate.get("invocation", {}).get("connection_url")
        intent_queries = [tool_name]
        if subtask_id == "execute_generated_project":
            intent_queries.extend(["execute assignment", "run tests", "execute project", "run benchmark"])
        else:
            intent_queries.extend(["evaluate assignment", "validate project", "score assignment"])

        try:
            await asyncio.to_thread(self._ensure_connection, resolved_connection_id, resolved_connection_url)
            resolved_tool_name, schema = await asyncio.to_thread(
                self.resolve_tool_name,
                connection_id=resolved_connection_id,
                requested_tool_name=tool_name,
                payload=payload,
                intent_queries=intent_queries,
            )
            response = await asyncio.to_thread(self._call_tool, resolved_connection_id, resolved_tool_name, payload)
            return {
                "status": "completed",
                "subtask_id": subtask_id,
                "agent": {
                    "agent_id": candidate.get("agent_id"),
                    "name": candidate.get("name"),
                    "source": candidate.get("source"),
                    "protocols": candidate.get("protocols", []),
                    "connection_id": resolved_connection_id,
                    "connection_url": resolved_connection_url,
                },
                "request_summary": {
                    "requested_tool_name": tool_name,
                    "tool_name": resolved_tool_name,
                    "artifact_count": len(payload.get("artifacts", [])),
                    "assignment_name": payload.get("assignment", {}).get("name"),
                },
                "tool_selection": {
                    "tool_name": resolved_tool_name,
                    "schema": schema,
                    "connection_id": resolved_connection_id,
                    "connection_url": resolved_connection_url,
                },
                "tool_schema": schema,
                "artifacts": [],
                outcome_field: {
                    "status": "completed",
                    "response": response,
                },
                "errors": None,
                "timing": {
                    "started_at": started_at,
                    "completed_at": _utcnow_iso(),
                },
            }
        except DelegationError as error:
            return {
                "status": "failed",
                "subtask_id": subtask_id,
                "agent": {
                    "agent_id": candidate.get("agent_id"),
                    "name": candidate.get("name"),
                    "source": candidate.get("source"),
                    "protocols": candidate.get("protocols", []),
                    "connection_id": resolved_connection_id,
                    "connection_url": resolved_connection_url,
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
                    "status": "failed",
                    "response": None,
                },
                "errors": {
                    "message": str(error),
                },
                "timing": {
                    "started_at": started_at,
                    "completed_at": _utcnow_iso(),
                },
            }

    async def evaluate_assignment_output(
        self,
        *,
        candidate: dict[str, Any],
        payload: dict[str, Any],
        connection_id: Optional[str] = None,
        connection_url: Optional[str] = None,
        tool_name: str = "evaluate",
    ) -> dict[str, Any]:
        """Run a delegated evaluation step and normalize the result."""
        return await self._invoke_assignment_subtask(
            candidate=candidate,
            payload=payload,
            connection_id=connection_id,
            connection_url=connection_url,
            tool_name=tool_name,
            subtask_id="validate_generated_project",
            outcome_field="validation",
        )

    async def execute_assignment_output(
        self,
        *,
        candidate: dict[str, Any],
        payload: dict[str, Any],
        connection_id: Optional[str] = None,
        connection_url: Optional[str] = None,
        tool_name: str = "execute",
    ) -> dict[str, Any]:
        """Run a delegated execution step and normalize the result."""
        return await self._invoke_assignment_subtask(
            candidate=candidate,
            payload=payload,
            connection_id=connection_id,
            connection_url=connection_url,
            tool_name=tool_name,
            subtask_id="execute_generated_project",
            outcome_field="execution",
        )


def delegated_evaluation_enabled_by_default() -> bool:
    """Return whether delegated evaluation should run by default."""
    return os.getenv("REMOTE_EVALUATION_ENABLED", "false").lower() == "true"


def delegated_execution_enabled_by_default() -> bool:
    """Return whether delegated execution should run by default."""
    return os.getenv("REMOTE_EXECUTION_ENABLED", "false").lower() == "true"