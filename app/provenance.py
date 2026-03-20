"""Helpers for attaching artifact provenance to local and delegated outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_artifact_provenance(
    task_response: dict[str, Any],
    *,
    delegated_execution: Optional[dict[str, Any]] = None,
    delegated_evaluation: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Build provenance entries for published artifacts and delegated evaluation outputs."""
    generated_at = _utcnow_iso()
    provenance_entries: list[dict[str, Any]] = []
    artifact_ids: list[str] = []

    for index, artifact in enumerate(task_response.get("artifacts", []), start=1):
        artifact_id = f"artifact-{index}:{artifact.get('kind', 'unknown')}"
        artifact_ids.append(artifact_id)
        validation_status = "pending"
        if delegated_evaluation:
            validation_status = "validated" if delegated_evaluation.get("status") == "completed" else "validation_failed"

        lineage = ["local_workflow_generation"]
        execution_status = None
        if delegated_execution:
            execution_status = delegated_execution.get("status")
            lineage.append(f"delegated_execution:{execution_status}")
        if delegated_evaluation:
            lineage.append(f"delegated_evaluation:{delegated_evaluation.get('status')}")

        provenance_entries.append(
            {
                "artifact_id": artifact_id,
                "kind": artifact.get("kind"),
                "producer": {
                    "type": "service",
                    "name": task_response.get("service", {}).get("name"),
                    "slug": task_response.get("service", {}).get("slug"),
                },
                "inputs": {
                    "assignment_id": task_response.get("assignment", {}).get("id"),
                    "route": task_response.get("route"),
                },
                "generated_at": generated_at,
                "validation_status": validation_status,
                "execution_status": execution_status,
                "lineage": lineage,
            }
        )

    if delegated_execution:
        provenance_entries.append(
            {
                "artifact_id": "delegated-execution:run-report",
                "kind": "delegated_execution",
                "producer": {
                    "type": "remote_agent",
                    "agent_id": delegated_execution.get("agent", {}).get("agent_id"),
                    "name": delegated_execution.get("agent", {}).get("name"),
                },
                "inputs": {
                    "executed_artifacts": artifact_ids,
                    "tool_name": delegated_execution.get("request_summary", {}).get("tool_name"),
                },
                "generated_at": delegated_execution.get("timing", {}).get("completed_at", generated_at),
                "validation_status": delegated_execution.get("status"),
                "lineage": artifact_ids,
            }
        )

    if delegated_evaluation:
        provenance_entries.append(
            {
                "artifact_id": "delegated-evaluation:validation-report",
                "kind": "delegated_evaluation",
                "producer": {
                    "type": "remote_agent",
                    "agent_id": delegated_evaluation.get("agent", {}).get("agent_id"),
                    "name": delegated_evaluation.get("agent", {}).get("name"),
                },
                "inputs": {
                    "evaluated_artifacts": artifact_ids,
                    "tool_name": delegated_evaluation.get("request_summary", {}).get("tool_name"),
                },
                "generated_at": delegated_evaluation.get("timing", {}).get("completed_at", generated_at),
                "validation_status": delegated_evaluation.get("status"),
                "lineage": artifact_ids,
            }
        )

    return provenance_entries