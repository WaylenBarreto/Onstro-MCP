from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from pm_mcp.api.pm_client import PMApiClient, PMApiClientError
from pm_mcp.config import get_app_settings
from pm_mcp.repositories.mock_repository import MockRepository

logger = logging.getLogger(__name__)


class CreateProjectInput(BaseModel):
    name: str = Field(..., description="Project name")
    description: str | None = None
    priority: str = "MEDIUM"
    start_date: str | None = None
    due_date: str | None = None
    owner_id: int | None = None


class UpdateProjectInput(BaseModel):
    project_id: int
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    owner_id: int | None = None
    start_date: str | None = None
    due_date: str | None = None


class ProjectTools:
    def __init__(self, repository: MockRepository | None = None):
        self.repository = repository
        self.settings = get_app_settings()
        self.client = PMApiClient() if not self.settings.mock_mode else None

    @staticmethod
    def _generate_description(name: str, priority: str | None = None, start_date: str | None = None, due_date: str | None = None) -> str:
        clean_name = " ".join(str(name).strip().split())
        if not clean_name:
            clean_name = "Project initiative"

        base = f"Plan and deliver the {clean_name} initiative with clear scope, milestones, ownership, and measurable outcomes."
        if priority:
            base = f"{base} Priority: {priority}."
        if start_date or due_date:
            date_bits = []
            if start_date:
                date_bits.append(f"start date {start_date}")
            if due_date:
                date_bits.append(f"due date {due_date}")
            base = f"{base} Timeline: {'; '.join(date_bits)}."
        return base

    async def create_project(self, *, name: str, description: str | None = None, priority: str = "MEDIUM", start_date: str | None = None, due_date: str | None = None, owner_id: int | None = None) -> dict[str, Any]:
        normalized_description = description.strip() if isinstance(description, str) else description
        if not normalized_description:
            normalized_description = self._generate_description(name=name, priority=priority, start_date=start_date, due_date=due_date)

        payload = {
            "name": name,
            "description": normalized_description,
            "priority": priority,
            "start_date": start_date,
            "due_date": due_date,
            "owner_id": owner_id,
        }
        if self.settings.mock_mode:
            project = await self.repository.create_project(payload)
            return {"success": True, "project": project}
        try:
            project = await self.client.create_project(payload)
            return {"success": True, "project": project}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def get_project(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            project = await self.repository.get_project(project_id)
            if not project:
                return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} was not found."}}
            return {"success": True, "project": project}
        try:
            project = await self.client.get_project(project_id)
            return {"success": True, "project": project}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def list_projects(self, *, status: str | None = None, priority: str | None = None, owner_id: int | None = None) -> dict[str, Any]:
        if self.settings.mock_mode:
            projects = await self.repository.get_projects()
            if status:
                projects = [p for p in projects if p.get("status") == status]
            if priority:
                projects = [p for p in projects if p.get("priority") == priority]
            if owner_id is not None:
                projects = [p for p in projects if p.get("owner_id") == owner_id]
            return {"success": True, "projects": projects}
        try:
            response = await self.client.list_projects({"status": status, "priority": priority, "owner_id": owner_id})
            return {"success": True, "projects": response}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def update_project(self, *, project_id: int, **fields: Any) -> dict[str, Any]:
        allowed = {"name", "description", "status", "priority", "owner_id", "start_date", "due_date"}
        filtered = {key: value for key, value in fields.items() if value is not None and key in allowed}
        if not filtered:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": "No project fields were supplied for update."}}
        if self.settings.mock_mode:
            project = await self.repository.update_project(project_id, filtered)
            if not project:
                return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} was not found."}}
            return {"success": True, "project": project}
        try:
            project = await self.client.update_project(project_id, filtered)
            return {"success": True, "project": project}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def delete_project(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            deleted = await self.repository.delete_project(project_id)
            if not deleted:
                return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} was not found."}}
            return {"success": True, "deleted": True, "project_id": project_id}
        try:
            deleted = await self.client.delete_project(project_id)
            return {"success": True, "deleted": True, "project_id": project_id, "response": deleted}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}


def register_project_tools(mcp, repository):
    tools = ProjectTools(repository)

    @mcp.tool(name="create_project", description="WRITE OPERATION — Create a new project. Use for startup planning or when the user asks to create a project. This modifies project data.")
    async def create_project_tool(name: str, description: str | None = None, priority: str = "MEDIUM", start_date: str | None = None, due_date: str | None = None, owner_id: int | None = None):
        return await tools.create_project(name=name, description=description, priority=priority, start_date=start_date, due_date=due_date, owner_id=owner_id)

    @mcp.tool(name="get_project", description="READ OPERATION — Retrieve a project's complete data from the PM API or mock repository.")
    async def get_project_tool(project_id: int):
        return await tools.get_project(project_id=project_id)

    @mcp.tool(name="list_projects", description="READ OPERATION — List projects with optional filters for status, priority, or owner_id.")
    async def list_projects_tool(status: str | None = None, priority: str | None = None, owner_id: int | None = None):
        return await tools.list_projects(status=status, priority=priority, owner_id=owner_id)

    @mcp.tool(name="update_project", description="WRITE OPERATION — Update only the supplied project fields. This modifies existing project data.")
    async def update_project_tool(project_id: int, name: str | None = None, description: str | None = None, status: str | None = None, priority: str | None = None, owner_id: int | None = None, start_date: str | None = None, due_date: str | None = None):
        return await tools.update_project(project_id=project_id, name=name, description=description, status=status, priority=priority, owner_id=owner_id, start_date=start_date, due_date=due_date)

    @mcp.tool(name="delete_project", description="DESTRUCTIVE OPERATION — Permanently delete a project. Require explicit user confirmation before use because this is destructive and irreversible.")
    async def delete_project_tool(project_id: int):
        return await tools.delete_project(project_id=project_id)
