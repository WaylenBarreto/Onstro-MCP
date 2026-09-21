from __future__ import annotations

import logging
from typing import Any

from pm_mcp.engines.assignment_engine import AssignmentEngine
from pm_mcp.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AssignmentTools:
    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository
        self.assignment_engine = AssignmentEngine()

    async def recommend_assignee(self, *, task_id: int | None = None, task_description: str | None = None, required_skills: list[str] | None = None, estimated_hours: float | None = None, deadline: str | None = None) -> dict[str, Any]:
        if task_id is not None:
            task = await self.repository.get_task(task_id)
            if not task:
                return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
        else:
            task = {"title": "General task", "description": task_description or "", "estimated_hours": estimated_hours or 8, "due_date": deadline, "required_skills": required_skills or []}
        members = await self.repository.list_team_members()
        project = None
        if task.get("project_id"):
            project = await self.repository.get_project(task["project_id"])
        project = project or {"team_members": members}
        recommendation = self.assignment_engine.recommend_assignee(task=task, team_members=members, project=project)
        return {"success": True, **recommendation}

    async def assign_task(self, *, task_id: int, member_id: int) -> dict[str, Any]:
        task = await self.repository.assign_task(task_id, member_id)
        if not task:
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} was not found."}}
        return {"success": True, "task": task}

    async def auto_assign_project(self, *, project_id: int, dry_run: bool = True) -> dict[str, Any]:
        project = await self.repository.get_project(project_id)
        if not project:
            return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} was not found."}}
        tasks = await self.repository.list_tasks(project_id)
        members = await self.repository.list_team_members()
        assignments = []
        for task in tasks:
            if task.get("assignee_id") is not None:
                continue
            recommendation = self.assignment_engine.recommend_assignee(task=task, team_members=members, project={"team_members": members})
            if recommendation["recommended_member"]:
                assignments.append({
                    "task_id": task["id"],
                    "recommended_member": recommendation["recommended_member"]["id"],
                    "score": recommendation["score"],
                })
        if dry_run:
            return {"success": True, "dry_run": True, "project_id": project_id, "assignments": assignments}
        for item in assignments:
            await self.repository.assign_task(item["task_id"], item["recommended_member"])
        return {"success": True, "dry_run": False, "project_id": project_id, "assignments": assignments}


def register_assignment_tools(mcp, repository):
    tools = AssignmentTools(repository)

    @mcp.tool(name="recommend_assignee", description="READ OPERATION — Deterministically score candidate team members using skill match, role fit, workload, availability, and deadline feasibility.")
    async def recommend_assignee_tool(task_id: int | None = None, task_description: str | None = None, required_skills: list[str] | None = None, estimated_hours: float | None = None, deadline: str | None = None):
        return await tools.recommend_assignee(task_id=task_id, task_description=task_description, required_skills=required_skills, estimated_hours=estimated_hours, deadline=deadline)

    @mcp.tool(name="assign_task", description="WRITE OPERATION — Assign a task to an existing team member.")
    async def assign_task_tool(task_id: int, member_id: int):
        return await tools.assign_task(task_id=task_id, member_id=member_id)

    @mcp.tool(name="auto_assign_project", description="WRITE OPERATION with dry_run support — Review project tasks and assign suitable members, previewing recommendations before applying them.")
    async def auto_assign_project_tool(project_id: int, dry_run: bool = True):
        return await tools.auto_assign_project(project_id=project_id, dry_run=dry_run)
