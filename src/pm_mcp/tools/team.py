from __future__ import annotations

from typing import Any

from pm_mcp.api.pm_client import PMApiClient, PMApiClientError
from pm_mcp.config import get_app_settings
from pm_mcp.repositories.mock_repository import MockRepository


class TeamTools:
    def __init__(self, repository: MockRepository | None = None):
        self.repository = repository
        self.settings = get_app_settings()
        self.client = PMApiClient() if not self.settings.mock_mode else None

    async def list_team_members(self) -> dict[str, Any]:
        if self.settings.mock_mode:
            members = await self.repository.list_team_members()
            return {"success": True, "members": members}
        try:
            members = await self.client.list_team_members()
            return {"success": True, "members": members}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def get_team_member(self, *, member_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            member = await self.repository.get_team_member(member_id)
            if not member:
                return {"success": False, "error": {"code": "TEAM_MEMBER_NOT_FOUND", "message": f"Member {member_id} was not found."}}
            return {"success": True, "member": member}
        try:
            member = await self.client.get_team_member(member_id)
            return {"success": True, "member": member}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def get_member_skills(self, *, member_id: int) -> dict[str, Any]:
        member = await self.get_team_member(member_id=member_id)
        if not member.get("success"):
            return member
        skills = member["member"].get("skills", [])
        return {"success": True, "member_id": member_id, "skills": skills}

    async def get_member_workload(self, *, member_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            member = await self.repository.get_team_member(member_id)
            if not member:
                return {"success": False, "error": {"code": "TEAM_MEMBER_NOT_FOUND", "message": f"Member {member_id} was not found."}}
            tasks = await self.repository.list_tasks()
            assigned = [task for task in tasks if task.get("assignee_id") == member_id and task.get("status") != "DONE"]
            assigned_hours = sum(float(task.get("estimated_hours", 0) or 0) for task in assigned)
            max_hours = float(member.get("max_weekly_hours", 40) or 40)
            utilization = round((assigned_hours / max_hours) * 100, 2) if max_hours else 0.0
            return {
                "success": True,
                "member_id": member_id,
                "assigned_hours": assigned_hours,
                "maximum_hours": max_hours,
                "utilization_percentage": utilization,
                "active_task_count": len(assigned),
                "overdue_task_count": sum(1 for task in assigned if task.get("due_date") is not None),
            }
        try:
            workload = await self.client.get_member_workload(member_id)
            return {"success": True, **workload}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}

    async def get_team_workload(self) -> dict[str, Any]:
        if self.settings.mock_mode:
            members = await self.repository.list_team_members()
            tasks = await self.repository.list_tasks()
            summary = []
            for member in members:
                assigned = [task for task in tasks if task.get("assignee_id") == member["id"] and task.get("status") != "DONE"]
                assigned_hours = sum(float(task.get("estimated_hours", 0) or 0) for task in assigned)
                max_hours = float(member.get("max_weekly_hours", 40) or 40)
                utilization = round((assigned_hours / max_hours) * 100, 2) if max_hours else 0.0
                summary.append({
                    "member_id": member["id"],
                    "name": member["name"],
                    "role": member.get("role"),
                    "assigned_hours": assigned_hours,
                    "maximum_hours": max_hours,
                    "utilization_percentage": utilization,
                    "active_task_count": len(assigned),
                    "overdue_task_count": sum(1 for task in assigned if task.get("due_date") is not None),
                })
            return {"success": True, "members": summary}
        try:
            workload = await self.client.get_team_workload()
            return {"success": True, **workload}
        except PMApiClientError as exc:
            return {"success": False, "error": {"code": exc.code, "message": exc.message}}


def register_team_tools(mcp, repository):
    tools = TeamTools(repository)

    @mcp.tool(name="list_team_members", description="READ OPERATION — Return team-member roster with roles, skills, availability, and current workload.")
    async def list_team_members_tool():
        return await tools.list_team_members()

    @mcp.tool(name="get_team_member", description="READ OPERATION — Retrieve full details for one team member.")
    async def get_team_member_tool(member_id: int):
        return await tools.get_team_member(member_id=member_id)

    @mcp.tool(name="get_member_skills", description="READ OPERATION — Return skills for a specific team member.")
    async def get_member_skills_tool(member_id: int):
        return await tools.get_member_skills(member_id=member_id)

    @mcp.tool(name="get_member_workload", description="READ OPERATION — Return assigned hours, capacity, utilization, and task counts for a team member.")
    async def get_member_workload_tool(member_id: int):
        return await tools.get_member_workload(member_id=member_id)

    @mcp.tool(name="get_team_workload", description="READ OPERATION — Return workload information across the entire team.")
    async def get_team_workload_tool():
        return await tools.get_team_workload()
