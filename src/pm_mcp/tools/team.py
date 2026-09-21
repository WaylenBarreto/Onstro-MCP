from __future__ import annotations

from typing import Any

from pm_mcp.repositories.base import BaseRepository


class TeamTools:
    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    async def list_team_members(self) -> dict[str, Any]:
        members = await self.repository.list_team_members()
        return {"success": True, "members": members}

    async def get_team_member(self, *, member_id: int) -> dict[str, Any]:
        member = await self.repository.get_team_member(member_id)
        if not member:
            return {"success": False, "error": {"code": "TEAM_MEMBER_NOT_FOUND", "message": f"Member {member_id} was not found."}}
        return {"success": True, "member": member}

    async def get_member_skills(self, *, member_id: int) -> dict[str, Any]:
        result = await self.get_team_member(member_id=member_id)
        if not result.get("success"):
            return result
        return {"success": True, "member_id": member_id, "skills": result["member"].get("skills", [])}

    async def get_member_workload(self, *, member_id: int) -> dict[str, Any]:
        member = await self.repository.get_team_member(member_id)
        if not member:
            return {"success": False, "error": {"code": "TEAM_MEMBER_NOT_FOUND", "message": f"Member {member_id} was not found."}}
        tasks = await self.repository.list_tasks()
        assigned = [t for t in tasks if t.get("assignee_id") == member_id and t.get("status") != "DONE"]
        assigned_hours = sum(float(t.get("estimated_hours") or 0) for t in assigned)
        max_hours = float(member.get("max_weekly_hours") or 40)
        utilization = round((assigned_hours / max_hours) * 100, 2) if max_hours else 0.0
        return {
            "success": True,
            "member_id": member_id,
            "assigned_hours": assigned_hours,
            "maximum_hours": max_hours,
            "utilization_percentage": utilization,
            "active_task_count": len(assigned),
            "overdue_task_count": sum(1 for t in assigned if t.get("due_date") is not None),
        }

    async def get_team_workload(self) -> dict[str, Any]:
        members = await self.repository.list_team_members()
        tasks = await self.repository.list_tasks()
        summary = []
        for m in members:
            assigned = [t for t in tasks if t.get("assignee_id") == m["id"] and t.get("status") != "DONE"]
            assigned_hours = sum(float(t.get("estimated_hours") or 0) for t in assigned)
            max_hours = float(m.get("max_weekly_hours") or 40)
            utilization = round((assigned_hours / max_hours) * 100, 2) if max_hours else 0.0
            summary.append({
                "member_id": m["id"],
                "name": m["name"],
                "role": m.get("role"),
                "assigned_hours": assigned_hours,
                "maximum_hours": max_hours,
                "utilization_percentage": utilization,
                "active_task_count": len(assigned),
                "overdue_task_count": sum(1 for t in assigned if t.get("due_date") is not None),
            })
        return {"success": True, "members": summary}


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
