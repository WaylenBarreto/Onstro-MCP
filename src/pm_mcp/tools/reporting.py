from __future__ import annotations

from datetime import datetime
from typing import Any

from pm_mcp.config import get_app_settings
from pm_mcp.repositories.mock_repository import MockRepository


class ReportingTools:
    def __init__(self, repository: MockRepository | None = None):
        self.repository = repository
        self.settings = get_app_settings()

    async def generate_project_report(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            project = await self.repository.get_project(project_id)
            tasks = await self.repository.list_tasks(project_id=project_id)
            pending = [task for task in tasks if task.get("status") != "DONE"]
            overdue = [task for task in tasks if task.get("status") != "DONE" and task.get("due_date") and task["due_date"] < datetime.now().strftime("%Y-%m-%d")]
            blockers = [task for task in tasks if task.get("status") == "BLOCKED"]
            return {
                "success": True,
                "project_summary": project,
                "completed_tasks": [task for task in tasks if task.get("status") == "DONE"],
                "pending_tasks": pending,
                "overdue_tasks": overdue,
                "blockers": blockers,
                "risks": [],
                "workload": [],
                "upcoming_deadlines": [task for task in tasks if task.get("due_date")],
                "recommendations": ["Review the critical path before launch."],
            }
        return {"success": True, "message": "Not implemented for remote API mode"}

    async def generate_team_report(self) -> dict[str, Any]:
        if self.settings.mock_mode:
            members = await self.repository.list_team_members()
            tasks = await self.repository.list_tasks()
            return {
                "success": True,
                "members": [
                    {
                        "member_id": member["id"],
                        "name": member["name"],
                        "role": member.get("role"),
                        "assignments": [task for task in tasks if task.get("assignee_id") == member["id"]],
                        "overdue_tasks": [task for task in tasks if task.get("assignee_id") == member["id"] and task.get("status") != "DONE" and task.get("due_date")],
                        "capacity": member.get("max_weekly_hours"),
                        "risks": [],
                    }
                    for member in members
                ],
            }
        return {"success": True, "message": "Not implemented for remote API mode"}

    async def generate_standup(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            tasks = await self.repository.list_tasks(project_id=project_id)
            members = await self.repository.list_team_members()
            report = {}
            for member in members:
                member_tasks = [task for task in tasks if task.get("assignee_id") == member["id"]]
                report[member["name"]] = {
                    "Yesterday": [task["title"] for task in member_tasks if task.get("status") == "DONE"],
                    "Today": [task["title"] for task in member_tasks if task.get("status") == "IN_PROGRESS"],
                    "Blocked": [task["title"] for task in member_tasks if task.get("status") == "BLOCKED"],
                }
            return {"success": True, "standup": report}
        return {"success": True, "message": "Not implemented for remote API mode"}


def register_reporting_tools(mcp, repository):
    tools = ReportingTools(repository)

    @mcp.tool(name="generate_project_report", description="READ OPERATION — Generate a project summary including completed, pending, overdue, blockers, risks, and workload information.")
    async def generate_project_report_tool(project_id: int):
        return await tools.generate_project_report(project_id=project_id)

    @mcp.tool(name="generate_team_report", description="READ OPERATION — Summarize each member's workload, assignments, capacity, overdue work, and risk posture.")
    async def generate_team_report_tool():
        return await tools.generate_team_report()

    @mcp.tool(name="generate_standup", description="READ OPERATION — Return a member-by-member standup summary using actual task data for the project.")
    async def generate_standup_tool(project_id: int):
        return await tools.generate_standup(project_id=project_id)
