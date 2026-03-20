"""SQLite-backed task storage for durable workflow state."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator, MutableMapping
from threading import RLock
from typing import Any


DEFAULT_TASK_STORE_PATH = ".data/task-store.sqlite3"


class SQLiteTaskStore(MutableMapping[str, dict[str, Any]]):
    """Persist task payloads in SQLite while presenting a mapping-like interface."""

    def __init__(self, db_path: str | None = None):
        configured_path = (db_path or os.getenv("TASK_STORE_PATH", DEFAULT_TASK_STORE_PATH)).strip()
        self.db_path = configured_path or DEFAULT_TASK_STORE_PATH
        self._lock = RLock()
        self._ensure_database()

    def _ensure_database(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_steps (
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (task_id, step_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_scorecards (
                    agent_id TEXT NOT NULL,
                    capability_family TEXT NOT NULL,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    blocked_count INTEGER NOT NULL DEFAULT 0,
                    total_count INTEGER NOT NULL DEFAULT 0,
                    last_status TEXT,
                    last_tool_name TEXT,
                    last_task_id TEXT,
                    last_step_id TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (agent_id, capability_family)
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _serialize(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True)

    @staticmethod
    def _deserialize(raw_payload: str) -> dict[str, Any]:
        return json.loads(raw_payload)

    @staticmethod
    def _normalize_step_payload(step: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(step)
        attempt_count = int(normalized.get("attempt_count") or 1)
        normalized.setdefault("attempt_count", attempt_count)
        normalized.setdefault("retry_count", max(attempt_count - 1, 0))
        normalized.setdefault("last_retry_at", None)
        normalized.setdefault("retry_history", [])
        return normalized

    def __getitem__(self, key: str) -> dict[str, Any]:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        serialized = self._serialize(value)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks (task_id, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(task_id)
                DO UPDATE SET payload = excluded.payload, updated_at = CURRENT_TIMESTAMP
                """,
                (key, serialized),
            )
            connection.commit()

    def __delitem__(self, key: str) -> None:
        with self._lock, self._connect() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE task_id = ?", (key,))
            connection.execute("DELETE FROM task_steps WHERE task_id = ?", (key,))
            connection.commit()
            if cursor.rowcount == 0:
                raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT task_id FROM tasks ORDER BY updated_at").fetchall()
        for row in rows:
            yield row[0]

    def __len__(self) -> int:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()
        return int(row[0] if row else 0)

    def get(self, key: str, default: dict[str, Any] | None = None) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM tasks WHERE task_id = ?",
                (key,),
            ).fetchone()
        if not row:
            return default
        return self._deserialize(row[0])

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM agent_scorecards")
            connection.execute("DELETE FROM task_steps")
            connection.execute("DELETE FROM tasks")
            connection.commit()

    def save_step(self, task_id: str, step: dict[str, Any]) -> None:
        serialized = self._serialize(step)
        position = int(step.get("position") or 0)
        step_id = str(step.get("step_id") or "").strip()
        if not step_id:
            raise ValueError("step_id is required")

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_steps (task_id, step_id, position, payload, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(task_id, step_id)
                DO UPDATE SET
                    position = excluded.position,
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (task_id, step_id, position, serialized),
            )
            connection.commit()

    def get_step(self, task_id: str, step_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM task_steps WHERE task_id = ? AND step_id = ?",
                (task_id, step_id),
            ).fetchone()
        if not row:
            return None
        return self._normalize_step_payload(self._deserialize(row[0]))

    def list_steps(self, task_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM task_steps WHERE task_id = ? ORDER BY position, updated_at",
                (task_id,),
            ).fetchall()
        return [self._normalize_step_payload(self._deserialize(row[0])) for row in rows]

    def record_agent_scorecard_event(
        self,
        *,
        agent_id: str,
        capability_family: str,
        status: str,
        tool_name: str | None = None,
        task_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        normalized_status = status.strip().lower()
        if normalized_status not in {"completed", "failed", "blocked"}:
            normalized_status = "failed"

        increments = {
            "success_count": 1 if normalized_status == "completed" else 0,
            "failure_count": 1 if normalized_status == "failed" else 0,
            "blocked_count": 1 if normalized_status == "blocked" else 0,
            "total_count": 1,
        }

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_scorecards (
                    agent_id,
                    capability_family,
                    success_count,
                    failure_count,
                    blocked_count,
                    total_count,
                    last_status,
                    last_tool_name,
                    last_task_id,
                    last_step_id,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(agent_id, capability_family)
                DO UPDATE SET
                    success_count = agent_scorecards.success_count + excluded.success_count,
                    failure_count = agent_scorecards.failure_count + excluded.failure_count,
                    blocked_count = agent_scorecards.blocked_count + excluded.blocked_count,
                    total_count = agent_scorecards.total_count + excluded.total_count,
                    last_status = excluded.last_status,
                    last_tool_name = excluded.last_tool_name,
                    last_task_id = excluded.last_task_id,
                    last_step_id = excluded.last_step_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    agent_id,
                    capability_family,
                    increments["success_count"],
                    increments["failure_count"],
                    increments["blocked_count"],
                    increments["total_count"],
                    normalized_status,
                    tool_name,
                    task_id,
                    step_id,
                ),
            )
            connection.commit()

    def get_agent_scorecard(self, agent_id: str, capability_family: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    agent_id,
                    capability_family,
                    success_count,
                    failure_count,
                    blocked_count,
                    total_count,
                    last_status,
                    last_tool_name,
                    last_task_id,
                    last_step_id,
                    updated_at
                FROM agent_scorecards
                WHERE agent_id = ? AND capability_family = ?
                """,
                (agent_id, capability_family),
            ).fetchone()

        if not row:
            return None

        success_count = int(row[2])
        total_count = int(row[5])
        success_rate = round(success_count / total_count, 3) if total_count else 0.0
        return {
            "agent_id": row[0],
            "capability_family": row[1],
            "success_count": success_count,
            "failure_count": int(row[3]),
            "blocked_count": int(row[4]),
            "total_count": total_count,
            "success_rate": success_rate,
            "last_status": row[6],
            "last_tool_name": row[7],
            "last_task_id": row[8],
            "last_step_id": row[9],
            "updated_at": row[10],
        }

    def list_agent_scorecards(self, capability_family: str | None = None) -> list[dict[str, Any]]:
        query = (
            "SELECT agent_id, capability_family FROM agent_scorecards WHERE capability_family = ? ORDER BY updated_at DESC"
            if capability_family
            else "SELECT agent_id, capability_family FROM agent_scorecards ORDER BY updated_at DESC"
        )
        params = (capability_family,) if capability_family else ()
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            self.get_agent_scorecard(row[0], row[1])
            for row in rows
            if self.get_agent_scorecard(row[0], row[1]) is not None
        ]