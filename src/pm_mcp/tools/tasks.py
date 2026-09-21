from __future__ import annotations

import logging
from typing import Any

from pm_mcp.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TaskTools:
    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    async def create_task(self, *, project_id: int, title: str, description: str | None = None, priority: str = "MEDIUM", estimated_hours: float | None = None, due_date: str | None = None, assignee_id: int | None = None, parent_task_id: int | None = None) -> dict[str, Any]:
        payload = {
            "project_id": project_id,
            "title": title,
            "description": description,
            "priority": priority,
            "estimated_hours": estimated_hours,
            "due_date": due_date,
            "assignee_id": assignee_id,
            "parent_task_id": parent_task_id,
            "dependencies": [],
        }
        task = await self.repository.create_task(payload)
        return {"success": True, "task": task}

    async def get_task(self, *, task_id: int) -> dict[str, Any]:
        task = await self.repository.get_task(task_id)
        if not task:
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
        return {"success": True, "task": task}

    async def list_tasks(self, *, project_id: int | None = None, status: str | None = None, priority: str | None = None, assignee_id: int | None = None) -> dict[str, Any]:
        tasks = await self.repository.list_tasks(project_id, status=status, priority=priority, assignee_id=assignee_id)
        return {"success": True, "tasks": tasks}

    async def update_task(self, *, task_id: int, title: str | None = None, description: str | None = None, status: str | None = None, priority: str | None = None, estimated_hours: float | None = None, due_date: str | None = None, assignee_id: int | None = None) -> dict[str, Any]:
        filtered = {k: v for k, v in {
            "title": title, "description": description, "status": status,
            "priority": priority, "estimated_hours": estimated_hours,
            "due_date": due_date, "assignee_id": assignee_id,
        }.items() if v is not None}
        if not filtered:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": "No task fields were supplied for update."}}
        task = await self.repository.update_task(task_id, filtered)
        if not task:
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
        return {"success": True, "task": task}

    async def delete_task(self, *, task_id: int) -> dict[str, Any]:
        deleted = await self.repository.delete_task(task_id)
        if not deleted:
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
        return {"success": True, "deleted": True, "task_id": task_id}

    async def complete_task(self, *, task_id: int) -> dict[str, Any]:
        task = await self.repository.update_task(task_id, {"status": "DONE"})
        if not task:
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
        return {"success": True, "task": task}

    async def create_subtask(self, *, parent_task_id: int, title: str, description: str | None = None, estimated_hours: float | None = None, priority: str = "MEDIUM", assignee_id: int | None = None, due_date: str | None = None) -> dict[str, Any]:
        return await self.create_task(project_id=0, title=title, description=description, priority=priority, estimated_hours=estimated_hours, due_date=due_date, assignee_id=assignee_id, parent_task_id=parent_task_id)

    async def log_time(self, *, task_id: int, member_id: int, hours_logged: float, description: str | None = None) -> dict[str, Any]:
        task = await self.repository.get_task(task_id)
        if not task:
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
        entry = await self.repository.log_time(task_id, member_id, hours_logged, description)
        return {"success": True, "time_log": entry}

    async def get_time_logs(self, *, task_id: int | None = None, member_id: int | None = None) -> dict[str, Any]:
        logs = await self.repository.list_time_logs(task_id=task_id, member_id=member_id)
        return {"success": True, "time_logs": logs}


def register_task_tools(mcp, repository):
    tools = TaskTools(repository)

    @mcp.tool(name="create_task", description="WRITE OPERATION — Create a task in a project.")
    async def create_task_tool(project_id: int, title: str, description: str | None = None, priority: str = "MEDIUM", estimated_hours: float | None = None, due_date: str | None = None, assignee_id: int | None = None, parent_task_id: int | None = None):
        return await tools.create_task(project_id=project_id, title=title, description=description, priority=priority, estimated_hours=estimated_hours, due_date=due_date, assignee_id=assignee_id, parent_task_id=parent_task_id)

    @mcp.tool(name="get_task", description="READ OPERATION — Get a detailed task record by ID.")
    async def get_task_tool(task_id: int):
        return await tools.get_task(task_id=task_id)

    @mcp.tool(name="list_tasks", description="READ OPERATION — List project tasks with optional filters for status, priority, and assignee.")
    async def list_tasks_tool(project_id: int | None = None, status: str | None = None, priority: str | None = None, assignee_id: int | None = None):
        return await tools.list_tasks(project_id=project_id, status=status, priority=priority, assignee_id=assignee_id)

    @mcp.tool(name="update_task", description="WRITE OPERATION — Update task fields. Only the supplied fields should change.")
    async def update_task_tool(task_id: int, title: str | None = None, description: str | None = None, status: str | None = None, priority: str | None = None, estimated_hours: float | None = None, due_date: str | None = None, assignee_id: int | None = None):
        return await tools.update_task(task_id=task_id, title=title, description=description, status=status, priority=priority, estimated_hours=estimated_hours, due_date=due_date, assignee_id=assignee_id)

    @mcp.tool(name="delete_task", description="DESTRUCTIVE OPERATION — Permanently delete a task. Require explicit user confirmation.")
    async def delete_task_tool(task_id: int):
        return await tools.delete_task(task_id=task_id)

    @mcp.tool(name="complete_task", description="WRITE OPERATION — Mark a task as completed.")
    async def complete_task_tool(task_id: int):
        return await tools.complete_task(task_id=task_id)

    @mcp.tool(name="create_subtask", description="WRITE OPERATION — Create a child task under a parent task.")
    async def create_subtask_tool(parent_task_id: int, title: str, description: str | None = None, estimated_hours: float | None = None, priority: str = "MEDIUM", assignee_id: int | None = None, due_date: str | None = None):
        return await tools.create_subtask(parent_task_id=parent_task_id, title=title, description=description, estimated_hours=estimated_hours, priority=priority, assignee_id=assignee_id, due_date=due_date)

    @mcp.tool(name="log_time", description="WRITE OPERATION — Log work hours against a task for a team member.")
    async def log_time_tool(task_id: int, member_id: int, hours_logged: float, description: str | None = None):
        return await tools.log_time(task_id=task_id, member_id=member_id, hours_logged=hours_logged, description=description)

    @mcp.tool(name="get_time_logs", description="READ OPERATION — Retrieve time logs by task_id or member_id.")
    async def get_time_logs_tool(task_id: int | None = None, member_id: int | None = None):
        return await tools.get_time_logs(task_id=task_id, member_id=member_id)
