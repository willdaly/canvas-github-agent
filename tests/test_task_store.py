from app.task_store import SQLiteTaskStore


def test_sqlite_task_store_persists_across_instances(tmp_path):
    db_path = tmp_path / "tasks.sqlite3"

    first = SQLiteTaskStore(str(db_path))
    first.clear()
    first["task-1"] = {"task_id": "task-1", "status": "queued"}

    second = SQLiteTaskStore(str(db_path))
    assert second["task-1"]["status"] == "queued"


def test_sqlite_task_store_clear_removes_tasks(tmp_path):
    db_path = tmp_path / "tasks.sqlite3"

    store = SQLiteTaskStore(str(db_path))
    store["task-1"] = {"task_id": "task-1", "status": "queued"}
    store.clear()

    assert store.get("task-1") is None


def test_sqlite_task_store_persists_steps(tmp_path):
    db_path = tmp_path / "tasks.sqlite3"

    store = SQLiteTaskStore(str(db_path))
    store.clear()
    store["task-1"] = {"task_id": "task-1", "status": "queued"}
    store.save_step(
        "task-1",
        {
            "task_id": "task-1",
            "step_id": "generate_primary_artifacts",
            "title": "Generate primary artifacts",
            "position": 1,
            "mode": "local",
            "capability_family": None,
            "status": "completed",
        },
    )

    second = SQLiteTaskStore(str(db_path))
    steps = second.list_steps("task-1")

    assert steps[0]["step_id"] == "generate_primary_artifacts"


def test_sqlite_task_store_persists_agent_scorecards(tmp_path):
    db_path = tmp_path / "tasks.sqlite3"

    store = SQLiteTaskStore(str(db_path))
    store.clear()
    store.record_agent_scorecard_event(
        agent_id="stub-evaluation-agent",
        capability_family="evaluation",
        status="completed",
        tool_name="grader.evaluate",
        task_id="task-1",
        step_id="validate_generated_project",
    )

    second = SQLiteTaskStore(str(db_path))
    scorecard = second.get_agent_scorecard("stub-evaluation-agent", "evaluation")

    assert scorecard is not None
    assert scorecard["success_rate"] == 1.0