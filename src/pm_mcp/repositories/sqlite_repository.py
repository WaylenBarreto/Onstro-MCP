"""
SQLite-backed repository — real persistent storage, no fake data.

All data survives server restarts. The database is created automatically at
the path specified by the DB_PATH env variable (default: pm_data.db in the
project root).
"""
from __future__ import annotations

import copy
import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from pm_mcp.repositories.base import BaseRepository

_DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "pm_data.db",
)

# Seed members — same roster as before; members are managed outside the tool set
_SEED_MEMBERS: list[dict[str, Any]] = [
    {
        "id": 1, "name": "Alice", "email": "alice@company.com",
        "role": "Project Manager",
        "skills": ["planning", "risk", "communication"],
        "availability": 0.8, "max_weekly_hours": 40, "current_workload": 0,
    },
    {
        "id": 2, "name": "Bob", "email": "bob@company.com",
        "role": "Backend Developer",
        "skills": ["python", "api", "database", "security"],
        "availability": 0.9, "max_weekly_hours": 40, "current_workload": 0,
    },
    {
        "id": 3, "name": "Carla", "email": "carla@company.com",
        "role": "Frontend Developer",
        "skills": ["react", "ux", "javascript", "html"],
        "availability": 0.7, "max_weekly_hours": 32, "current_workload": 0,
    },
    {
        "id": 4, "name": "David", "email": "david@company.com",
        "role": "QA Engineer",
        "skills": ["testing", "automation", "security"],
        "availability": 0.85, "max_weekly_hours": 38, "current_workload": 0,
    },
    {
        "id": 5, "name": "Sarah", "email": "sarah@company.com",
        "role": "Full Stack Developer",
        "skills": ["python", "react", "api", "ux"],
        "availability": 0.95, "max_weekly_hours": 40, "current_workload": 0,
    },
]

_DDL = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    status      TEXT    NOT NULL DEFAULT 'PLANNING',
    priority    TEXT    NOT NULL DEFAULT 'MEDIUM',
    owner_id    INTEGER,
    start_date  TEXT,
    due_date    TEXT,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     INTEGER NOT NULL,
    title          TEXT    NOT NULL,
    description    TEXT,
    status         TEXT    NOT NULL DEFAULT 'TODO',
    priority       TEXT    NOT NULL DEFAULT 'MEDIUM',
    assignee_id    INTEGER,
    estimated_hours REAL,
    due_date       TEXT,
    parent_task_id INTEGER,
    dependencies   TEXT    NOT NULL DEFAULT '[]',
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS team_members (
    id               INTEGER PRIMARY KEY,
    name             TEXT    NOT NULL,
    email            TEXT,
    role             TEXT,
    skills           TEXT    NOT NULL DEFAULT '[]',
    availability     REAL    NOT NULL DEFAULT 1.0,
    max_weekly_hours REAL    NOT NULL DEFAULT 40.0,
    current_workload REAL    NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS time_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id      INTEGER NOT NULL,
    member_id    INTEGER NOT NULL,
    hours_logged REAL    NOT NULL,
    description  TEXT,
    logged_at    TEXT    NOT NULL
);
"""


def _row_to_dict(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict[str, Any]:
    return dict(zip([col[0] for col in cursor.description], row))


def _parse_json_field(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


class SqliteRepository(BaseRepository):
    """
    Thread-safe synchronous SQLite repository using a single connection
    with WAL journal mode for concurrent reads.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.environ.get("DB_PATH", _DEFAULT_DB)
        self._conn: sqlite3.Connection | None = None
        # Initialize connection and seed tables
        _ = self.conn
        self._seed_members()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=30.0,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_DDL)
            self._conn.commit()
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ── internal helpers ──────────────────────────────────────────────────────

    def _seed_members(self) -> None:
        """Insert team members if the table is empty."""
        cur = self.conn.execute("SELECT COUNT(*) FROM team_members")
        if cur.fetchone()[0] == 0:
            for m in _SEED_MEMBERS:
                self.conn.execute(
                    """INSERT INTO team_members
                       (id, name, email, role, skills, availability,
                        max_weekly_hours, current_workload)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        m["id"], m["name"], m["email"], m["role"],
                        json.dumps(m["skills"]),
                        m["availability"], m["max_weekly_hours"], m["current_workload"],
                    ),
                )
            self.conn.commit()

    def _project_row(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        return d

    def _task_row(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["dependencies"] = _parse_json_field(d.get("dependencies"), [])
        return d

    def _member_row(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["skills"] = _parse_json_field(d.get("skills"), [])
        return d

    # ── workload helper ───────────────────────────────────────────────────────

    def _refresh_workload(self, member_id: int) -> None:
        """Recalculate current_workload as sum of estimated_hours of active tasks."""
        cur = self.conn.execute(
            """SELECT COALESCE(SUM(estimated_hours), 0)
               FROM tasks
               WHERE assignee_id = ? AND status NOT IN ('DONE', 'CANCELLED')""",
            (member_id,),
        )
        total = cur.fetchone()[0] or 0.0
        self.conn.execute(
            "UPDATE team_members SET current_workload = ? WHERE id = ?",
            (total, member_id),
        )

    # ── Projects ──────────────────────────────────────────────────────────────

    async def get_projects(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM projects ORDER BY id")
        return [self._project_row(r) for r in cur.fetchall()]

    async def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            """INSERT INTO projects
               (name, description, status, priority, owner_id, start_date, due_date,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload.get("name", ""),
                payload.get("description"),
                payload.get("status", "PLANNING"),
                payload.get("priority", "MEDIUM"),
                payload.get("owner_id"),
                payload.get("start_date"),
                payload.get("due_date"),
                payload.get("created_at", now),
                now,
            ),
        )
        self.conn.commit()
        new_id = cur.lastrowid
        return await self.get_project(new_id)  # type: ignore[return-value]

    async def get_project(self, project_id: int) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        return self._project_row(row) if row else None

    async def update_project(
        self, project_id: int, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        allowed = {"name", "description", "status", "priority", "owner_id",
                   "start_date", "due_date"}
        update = {k: v for k, v in fields.items() if k in allowed}
        if not update:
            return await self.get_project(project_id)
        update["updated_at"] = datetime.now().isoformat()
        cols = ", ".join(f"{k} = ?" for k in update)
        vals = list(update.values()) + [project_id]
        self.conn.execute(f"UPDATE projects SET {cols} WHERE id = ?", vals)
        self.conn.commit()
        return await self.get_project(project_id)

    async def delete_project(self, project_id: int) -> bool:
        # Cascade-delete tasks first
        self.conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        cur = self.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # ── Tasks ─────────────────────────────────────────────────────────────────

    async def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now().isoformat()
        deps = json.dumps(payload.get("dependencies", []))
        cur = self.conn.execute(
            """INSERT INTO tasks
               (project_id, title, description, status, priority, assignee_id,
                estimated_hours, due_date, parent_task_id, dependencies,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload.get("project_id"),
                payload.get("title", ""),
                payload.get("description"),
                payload.get("status", "TODO"),
                payload.get("priority", "MEDIUM"),
                payload.get("assignee_id"),
                payload.get("estimated_hours"),
                payload.get("due_date"),
                payload.get("parent_task_id"),
                deps,
                now, now,
            ),
        )
        self.conn.commit()
        new_id = cur.lastrowid
        # Update workload for assignee
        if payload.get("assignee_id"):
            self._refresh_workload(payload["assignee_id"])
            self.conn.commit()
        return await self.get_task(new_id)  # type: ignore[return-value]

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        return self._task_row(row) if row else None

    async def list_tasks(
        self, project_id: int | None = None, **filters: Any
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list[Any] = []
        if project_id is not None:
            query += " AND project_id = ?"
            params.append(project_id)
        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])
        if filters.get("priority"):
            query += " AND priority = ?"
            params.append(filters["priority"])
        if filters.get("assignee_id") is not None:
            query += " AND assignee_id = ?"
            params.append(filters["assignee_id"])
        query += " ORDER BY id"
        cur = self.conn.execute(query, params)
        return [self._task_row(r) for r in cur.fetchall()]

    async def update_task(
        self, task_id: int, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        allowed = {"title", "description", "status", "priority", "assignee_id",
                   "estimated_hours", "due_date", "parent_task_id", "dependencies"}
        update: dict[str, Any] = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            update[k] = json.dumps(v) if k == "dependencies" else v
        if not update:
            return await self.get_task(task_id)
        update["updated_at"] = datetime.now().isoformat()
        cols = ", ".join(f"{k} = ?" for k in update)
        vals = list(update.values()) + [task_id]
        self.conn.execute(f"UPDATE tasks SET {cols} WHERE id = ?", vals)
        self.conn.commit()
        # Refresh workload for old and new assignee
        old = await self.get_task(task_id)
        if old and old.get("assignee_id"):
            self._refresh_workload(old["assignee_id"])
        if fields.get("assignee_id") and fields["assignee_id"] != (old or {}).get("assignee_id"):
            self._refresh_workload(fields["assignee_id"])
        self.conn.commit()
        return await self.get_task(task_id)

    async def delete_task(self, task_id: int) -> bool:
        task = await self.get_task(task_id)
        cur = self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        if task and task.get("assignee_id"):
            self._refresh_workload(task["assignee_id"])
            self.conn.commit()
        return cur.rowcount > 0

    # ── Team members ──────────────────────────────────────────────────────────

    async def list_team_members(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM team_members ORDER BY id")
        return [self._member_row(r) for r in cur.fetchall()]

    async def get_team_member(self, member_id: int) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM team_members WHERE id = ?", (member_id,)
        )
        row = cur.fetchone()
        return self._member_row(row) if row else None

    async def assign_task(self, task_id: int, member_id: int) -> dict[str, Any] | None:
        task = await self.get_task(task_id)
        if not task:
            return None
        old_assignee = task.get("assignee_id")
        self.conn.execute(
            "UPDATE tasks SET assignee_id = ?, updated_at = ? WHERE id = ?",
            (member_id, datetime.now().isoformat(), task_id),
        )
        self.conn.commit()
        # Refresh workload for both old and new assignee
        if old_assignee:
            self._refresh_workload(old_assignee)
        self.conn.commit()
        self._refresh_workload(member_id)
        self.conn.commit()
        return await self.get_task(task_id)

    # ── Time Logs ─────────────────────────────────────────────────────────────

    async def log_time(
        self, task_id: int, member_id: int, hours_logged: float, description: str | None = None
    ) -> dict[str, Any]:
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            """INSERT INTO time_logs (task_id, member_id, hours_logged, description, logged_at)
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, member_id, hours_logged, description, now),
        )
        self.conn.commit()
        log_id = cur.lastrowid
        return {
            "id": log_id,
            "task_id": task_id,
            "member_id": member_id,
            "hours_logged": hours_logged,
            "description": description or "",
            "logged_at": now,
        }

    async def list_time_logs(
        self, task_id: int | None = None, member_id: int | None = None
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM time_logs WHERE 1=1"
        params: list[Any] = []
        if task_id is not None:
            query += " AND task_id = ?"
            params.append(task_id)
        if member_id is not None:
            query += " AND member_id = ?"
            params.append(member_id)
        query += " ORDER BY id DESC"
        cur = self.conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
