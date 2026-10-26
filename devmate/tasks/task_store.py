from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from devmate.observability.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """
    All valid states a task can be in.
    PENDING -> IN_PROGRESS -> COMPLETED
    Failure with retries left -> PENDING
    Failure with no retries left -> FAILED
    Dependency failed -> BLOCKED
    Skipped by user -> SKIPPED
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TaskType(str, Enum):
    DESIGN = "design"
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    INTEGRATE = "integrate"
    CONFIGURE = "configure"


@dataclass
class Task:
    id: str
    project_id: str
    title: str
    description: str
    task_type: str
    status: str = TaskStatus.PENDING
    depends_on: str = "[]"
    output_files: str = "[]"
    result: str | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    execution_order: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None


class SQLiteTaskStore:
    """Authoritative SQLite persistence layer for task tracking."""

    def __init__(self, db_path: str = ".devmate/tasks.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._setup_db()
        logger.info(f"SQLiteTaskStore initialised at {db_path}")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _setup_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    goal        TEXT NOT NULL,
                    plan_json   TEXT,
                    status      TEXT DEFAULT 'planning',
                    created_at  REAL DEFAULT (unixepoch()),
                    approved_at REAL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id                  TEXT PRIMARY KEY,
                    project_id          TEXT REFERENCES projects(id),
                    title               TEXT NOT NULL,
                    description         TEXT NOT NULL,
                    task_type           TEXT NOT NULL,
                    status              TEXT DEFAULT 'pending',
                    depends_on          TEXT DEFAULT '[]',
                    output_files        TEXT DEFAULT '[]',
                    acceptance_criteria TEXT DEFAULT '[]',
                    result              TEXT,
                    error               TEXT,
                    retry_count         INTEGER DEFAULT 0,
                    max_retries         INTEGER DEFAULT 3,
                    execution_order     INTEGER DEFAULT 0,
                    created_at          REAL DEFAULT (unixepoch()),
                    started_at          REAL,
                    completed_at        REAL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_project
                    ON tasks(project_id, status);
            """)

    def create_project(self, goal: str, plan) -> str:
        project_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO projects(id, name, goal, plan_json, status) VALUES (?,?,?,?,?)",
                (project_id, plan.project_name, goal, plan.model_dump_json(), "approved")
            )
            for i, pt in enumerate(plan.tasks):
                conn.execute(
                    """INSERT INTO tasks
                       (id, project_id, title, description, task_type,
                        depends_on, output_files, acceptance_criteria, execution_order)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        pt.id, project_id, pt.title, pt.description,
                        pt.task_type.value,
                        json.dumps(pt.depends_on),
                        json.dumps(pt.output_files),
                        json.dumps(pt.acceptance_criteria),
                        i,
                    )
                )
        logger.info(f"Project {project_id} created with {len(plan.tasks)} tasks")
        return project_id

    def get_latest_approved_project(self) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM projects WHERE status='approved' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return row["id"] if row else None

    def claim_task(self, task_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE tasks
                   SET status     = 'in_progress',
                       started_at = unixepoch()
                   WHERE id = ? AND status = 'pending'""",
                (task_id,)
            )
        return cur.rowcount == 1

    def complete_task(self, task_id: str, result: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE tasks
                   SET status       = 'completed',
                       result       = ?,
                       completed_at = unixepoch()
                   WHERE id = ?""",
                (result, task_id)
            )
        logger.info(f"Task {task_id} completed")

    def fail_task(self, task_id: str, error: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE tasks
                   SET retry_count = retry_count + 1,
                       error       = ?,
                       status      = CASE
                           WHEN retry_count + 1 < max_retries THEN 'pending'
                           ELSE 'failed'
                       END,
                       started_at  = NULL
                   WHERE id = ?""",
                (error, task_id)
            )
        logger.info(f"Task {task_id} failed: {error[:80]}")

    def block_task(self, task_id: str, reason: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE tasks SET status='blocked', error=? WHERE id=?",
                (reason, task_id)
            )

    def get_ready_tasks(self, project_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE project_id = ? AND status = 'pending'
                   ORDER BY execution_order""",
                (project_id,)
            ).fetchall()

        ready = []
        for row in rows:
            deps = json.loads(row["depends_on"])
            if self._all_deps_done(project_id, deps):
                ready.append(dict(row))
        return ready

    def _all_deps_done(self, project_id: str, dep_ids: list[str]) -> bool:
        if not dep_ids:
            return True
        placeholders = ",".join(["?"] * len(dep_ids))
        with self._conn() as conn:
            row = conn.execute(
                f"""SELECT COUNT(*) FROM tasks
                    WHERE id IN ({placeholders})
                      AND status NOT IN ('completed', 'skipped')""",
                dep_ids
            ).fetchone()
        return row[0] == 0

    def get_all_tasks(self, project_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY execution_order",
                (project_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_progress(self, project_id: str) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as n FROM tasks WHERE project_id=? GROUP BY status",
                (project_id,)
            ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def get_dep_results(self, dep_ids: list[str]) -> list[dict]:
        if not dep_ids:
            return []
        placeholders = ",".join(["?"] * len(dep_ids))
        with self._conn() as conn:
            rows = conn.execute(
                f"""SELECT id, title, result FROM tasks
                    WHERE id IN ({placeholders})
                      AND status = 'completed'""",
                dep_ids,
            ).fetchall()
        return [dict(r) for r in rows]
