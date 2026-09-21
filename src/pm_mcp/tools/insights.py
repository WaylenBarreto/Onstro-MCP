from __future__ import annotations

from datetime import datetime
from typing import Any

from pm_mcp.repositories.base import BaseRepository


class InsightsTools:
    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    async def get_member_insights(self, *, member_id: int) -> dict[str, Any]:
        member = await self.repository.get_team_member(member_id)
        if not member:
            return {"success": False, "message": f"Member with ID {member_id} not found."}

        tasks = await self.repository.list_tasks(assignee_id=member_id)
        completed_tasks = [t for t in tasks if t.get("status") == "DONE"]
        pending_tasks = [t for t in tasks if t.get("status") != "DONE"]
        now_str = datetime.now().strftime("%Y-%m-%d")
        overdue_tasks = [
            t for t in pending_tasks
            if t.get("due_date") and t["due_date"] < now_str
        ]

        actual_logs = []
        if hasattr(self.repository, "list_time_logs"):
            try:
                actual_logs = await self.repository.list_time_logs(member_id=member_id)
            except Exception:
                actual_logs = []
        actual_hours_logged = sum(float(tl.get("hours_logged") or 0) for tl in actual_logs)

        completed_hours = sum(float(t.get("estimated_hours") or 0) for t in completed_tasks)
        pending_hours = sum(float(t.get("estimated_hours") or 0) for t in pending_tasks)
        total_hours = sum(float(t.get("estimated_hours") or 0) for t in tasks)

        # Use actual logged hours if available, else completed estimated hours
        hours_worked = actual_hours_logged if actual_hours_logged > 0 else completed_hours

        is_flagged = len(overdue_tasks) > 0 or (len(pending_tasks) > 0 and len(completed_tasks) == 0)
        flag_reasons = []
        if len(overdue_tasks) > 0:
            flag_reasons.append(f"Has {len(overdue_tasks)} overdue incomplete task(s)")
        if len(pending_tasks) > 0 and len(completed_tasks) == 0:
            flag_reasons.append("No tasks completed yet for assigned work")
        flag_reason_str = "; ".join(flag_reasons) if is_flagged else "On track"

        return {
            "success": True,
            "member": {
                "id": member["id"],
                "name": member["name"],
                "role": member.get("role"),
                "max_weekly_hours": member.get("max_weekly_hours", 40),
                "flagged": is_flagged,
                "flag_reason": flag_reason_str,
            },
            "insights": {
                "total_assigned_tasks": len(tasks),
                "completed_tasks_count": len(completed_tasks),
                "pending_tasks_count": len(pending_tasks),
                "overdue_tasks_count": len(overdue_tasks),
                "hours_worked": round(completed_hours, 2),
                "pending_hours": round(pending_hours, 2),
                "total_estimated_hours": round(total_hours, 2),
                "completion_rate": round(len(completed_tasks) / len(tasks) * 100, 2) if tasks else 0.0,
                "active_projects": list({t.get("project_id") for t in tasks}),
            },
            "pending_tasks": pending_tasks,
            "recent_activity": sorted(tasks, key=lambda t: t.get("updated_at", ""), reverse=True)[:5],
        }

    async def get_project_insights(self, *, project_id: int) -> dict[str, Any]:
        project = await self.repository.get_project(project_id)
        if not project:
            return {"success": False, "message": f"Project with ID {project_id} not found."}

        tasks = await self.repository.list_tasks(project_id=project_id)
        members = await self.repository.list_team_members()

        completed_tasks = [t for t in tasks if t.get("status") == "DONE"]
        blocked_tasks = [t for t in tasks if t.get("status") == "BLOCKED"]
        now_str = datetime.now().strftime("%Y-%m-%d")
        overdue_tasks = [
            t for t in tasks
            if t.get("status") != "DONE" and t.get("due_date") and t["due_date"] < now_str
        ]

        member_activity: dict[int, dict[str, Any]] = {}
        for t in tasks:
            aid = t.get("assignee_id")
            if aid:
                if aid not in member_activity:
                    name = next((m["name"] for m in members if m["id"] == aid), f"User {aid}")
                    member_activity[aid] = {"name": name, "tasks_assigned": 0, "tasks_completed": 0}
                member_activity[aid]["tasks_assigned"] += 1
                if t.get("status") == "DONE":
                    member_activity[aid]["tasks_completed"] += 1

        most_active = sorted(member_activity.values(), key=lambda x: x["tasks_completed"], reverse=True)
        completion_rate = round(len(completed_tasks) / len(tasks) * 100, 2) if tasks else 0.0

        report_items: list[str] = []
        if blocked_tasks:
            report_items.append(f"{len(blocked_tasks)} tasks are currently BLOCKED.")
        if overdue_tasks:
            report_items.append(f"{len(overdue_tasks)} tasks are OVERDUE.")
        if completion_rate < 50 and project.get("due_date") and project["due_date"] < now_str:
            report_items.append("Project is past due and completion rate is below 50%.")

        return {
            "success": True,
            "project": {
                "id": project["id"],
                "name": project["name"],
                "description": project.get("description", ""),
                "status": project.get("status", "PLANNING"),
                "priority": project.get("priority", "MEDIUM"),
            },
            "insights": {
                "total_tasks": len(tasks),
                "completed_tasks": len(completed_tasks),
                "blocked_tasks": len(blocked_tasks),
                "overdue_tasks": len(overdue_tasks),
                "completion_rate": completion_rate,
            },
            "member_activity": most_active,
            "items_to_report": report_items or ["Project is on track. No critical items to report."],
        }


def register_insights_tools(mcp, repository):
    tools = InsightsTools(repository)

    @mcp.tool(name="get_member_insights", description="READ OPERATION — Get detailed insights for a specific team member, including their workload, completed/pending tasks, active time, and recent activity.")
    async def get_member_insights_tool(member_id: int):
        return await tools.get_member_insights(member_id=member_id)

    @mcp.tool(name="get_project_insights", description="READ OPERATION — Analyze a project to see overall progress, most active team members, completion rate, and critical items to report (like blocked or overdue tasks).")
    async def get_project_insights_tool(project_id: int):
        return await tools.get_project_insights(project_id=project_id)
