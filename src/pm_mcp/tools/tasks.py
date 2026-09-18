from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from pm_mcp.api.pm_client import PMApiClient, PMApiClientError
from pm_mcp.config import get_app_settings
from pm_mcp.repositories.mock_repository import MockRepository

logger = logging.getLogger(__name__)


class CreateTaskInput(BaseModel):
    project_id: int
    title: str
    description: str | None = None
    priority: str = "MEDIUM"
    estimated_hours: float | None = None
    due_date: str | None = None
    assignee_id: int | None = None
    parent_task_id: int | None = None


class TaskTools:
    def __init__(self, repository: MockRepository | None = None):
        self.repository = repository
        self.settings = get_app_settings()
        self.client = PMApiClient() if not self.settings.mock_mode else None

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
        if self.settings.mock_mode:
            task = await self.repository.create_task(payload)
            return {"success": True, "task": task}
        try:
            task = await self.client.create_task(payload)
            return {"success": True, "task": task}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def get_task(self, *, task_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            task = await self.repository.get_task(task_id)
            if not task:
                return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
            return {"success": True, "task": task}
        try:
            task = await self.client.get_task(task_id)
            return {"success": True, "task": task}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def list_tasks(self, *, project_id: int | None = None, status: str | None = None, priority: str | None = None, assignee_id: int | None = None) -> dict[str, Any]:
        if self.settings.mock_mode:
            tasks = await self.repository.list_tasks(project_id, status=status, priority=priority, assignee_id=assignee_id)
            return {"success": True, "tasks": tasks}
        try:
            response = await self.client.list_tasks(project_id=project_id, filters={"status": status, "priority": priority, "assignee_id": assignee_id})
            return {"success": True, "tasks": response}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def update_task(self, *, task_id: int, title: str | None = None, description: str | None = None, status: str | None = None, priority: str | None = None, estimated_hours: float | None = None, due_date: str | None = None, assignee_id: int | None = None) -> dict[str, Any]:
        filtered = {key: value for key, value in {"title": title, "description": description, "status": status, "priority": priority, "estimated_hours": estimated_hours, "due_date": due_date, "assignee_id": assignee_id}.items() if value is not None}
        if not filtered:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": "No task fields were supplied for update."}}
        if self.settings.mock_mode:
            task = await self.repository.update_task(task_id, filtered)
            if not task:
                return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
            return {"success": True, "task": task}
        try:
            task = await self.client.update_task(task_id, filtered)
            return {"success": True, "task": task}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def delete_task(self, *, task_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            deleted = await self.repository.delete_task(task_id)
            if not deleted:
                return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
            return {"success": True, "deleted": True, "task_id": task_id}
        try:
            deleted = await self.client.delete_task(task_id)
            return {"success": True, "deleted": True, "task_id": task_id, "response": deleted}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def complete_task(self, *, task_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            task = await self.repository.update_task(task_id, {"status": "DONE"})
            if not task:
                return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
            return {"success": True, "task": task}
        try:
            return {"success": True, "task": await self.client.complete_task(task_id)}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def create_subtask(self, *, parent_task_id: int, title: str, description: str | None = None, estimated_hours: float | None = None, priority: str = "MEDIUM", assignee_id: int | None = None, due_date: str | None = None) -> dict[str, Any]:
        return await self.create_task(project_id=0, title=title, description=description, priority=priority, estimated_hours=estimated_hours, due_date=due_date, assignee_id=assignee_id, parent_task_id=parent_task_id)


def register_task_tools(mcp, repository):
    tools = TaskTools(repository)

    @mcp.tool(name="create_task", description="WRITE OPERATION — Create a task in a project. Use when the user asks to plan or build work items. This modifies project data.")
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

    @mcp.tool(name="delete_task", description="DESTRUCTIVE OPERATION — Permanently delete a task. Require explicit user confirmation before use because this is destructive.")
    async def delete_task_tool(task_id: int):
        return await tools.delete_task(task_id=task_id)

    @mcp.tool(name="complete_task", description="WRITE OPERATION — Mark a task as completed.")
    async def complete_task_tool(task_id: int):
        return await tools.complete_task(task_id=task_id)

    @mcp.tool(name="create_subtask", description="WRITE OPERATION — Create a child task under a parent task. This is a subtask and modifies project work structure.")
    async def create_subtask_tool(parent_task_id: int, title: str, description: str | None = None, estimated_hours: float | None = None, priority: str = "MEDIUM", assignee_id: int | None = None, due_date: str | None = None):
        return await tools.create_subtask(parent_task_id=parent_task_id, title=title, description=description, estimated_hours=estimated_hours, priority=priority, assignee_id=assignee_id, due_date=due_date)
