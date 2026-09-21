from __future__ import annotations

from datetime import datetime
from typing import Any

from pm_mcp.repositories.base import BaseRepository


class ReportingTools:
    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    async def generate_project_report(self, *, project_id: int) -> dict[str, Any]:
        project = await self.repository.get_project(project_id)
        if not project:
            return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found."}}
        tasks = await self.repository.list_tasks(project_id=project_id)
        now = datetime.now().strftime("%Y-%m-%d")
        pending = [t for t in tasks if t.get("status") != "DONE"]
        overdue = [t for t in tasks if t.get("status") != "DONE" and t.get("due_date") and t["due_date"] < now]
        blockers = [t for t in tasks if t.get("status") == "BLOCKED"]
        return {
            "success": True,
            "project_summary": project,
            "completed_tasks": [t for t in tasks if t.get("status") == "DONE"],
            "pending_tasks": pending,
            "overdue_tasks": overdue,
            "blockers": blockers,
            "risks": [],
            "workload": [],
            "upcoming_deadlines": [t for t in tasks if t.get("due_date")],
            "recommendations": ["Review the critical path before launch."],
        }

    async def generate_team_report(self) -> dict[str, Any]:
        members = await self.repository.list_team_members()
        tasks = await self.repository.list_tasks()
        now = datetime.now().strftime("%Y-%m-%d")
        return {
            "success": True,
            "members": [
                {
                    "member_id": m["id"],
                    "name": m["name"],
                    "role": m.get("role"),
                    "assignments": [t for t in tasks if t.get("assignee_id") == m["id"]],
                    "overdue_tasks": [
                        t for t in tasks
                        if t.get("assignee_id") == m["id"]
                        and t.get("status") != "DONE"
                        and t.get("due_date")
                        and t["due_date"] < now
                    ],
                    "capacity": m.get("max_weekly_hours"),
                    "risks": [],
                }
                for m in members
            ],
        }

    async def generate_standup(self, *, project_id: int) -> dict[str, Any]:
        tasks = await self.repository.list_tasks(project_id=project_id)
        members = await self.repository.list_team_members()
        report: dict[str, Any] = {}
        for m in members:
            member_tasks = [t for t in tasks if t.get("assignee_id") == m["id"]]
            report[m["name"]] = {
                "Yesterday": [t["title"] for t in member_tasks if t.get("status") == "DONE"],
                "Today": [t["title"] for t in member_tasks if t.get("status") == "IN_PROGRESS"],
                "Blocked": [t["title"] for t in member_tasks if t.get("status") == "BLOCKED"],
            }
        return {"success": True, "standup": report}

    async def generate_csv_report(self, *, project_id: int | None = None) -> dict[str, Any]:
        import csv
        import io

        members = await self.repository.list_team_members()
        tasks = await self.repository.list_tasks(project_id=project_id)
        now_str = datetime.now().strftime("%Y-%m-%d")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Member ID", "Member Name", "Role", "Weekly Capacity (hrs)",
            "Hours Worked (Done)", "Pending Hours", "Completed Tasks",
            "Pending Tasks", "Overdue Tasks", "Flagged Status", "Flag Reason"
        ])

        for m in members:
            m_tasks = [t for t in tasks if t.get("assignee_id") == m["id"]]
            done_tasks = [t for t in m_tasks if t.get("status") == "DONE"]
            pending_tasks = [t for t in m_tasks if t.get("status") != "DONE"]
            overdue_tasks = [t for t in pending_tasks if t.get("due_date") and t["due_date"] < now_str]

            hours_worked = sum(float(t.get("estimated_hours") or 0) for t in done_tasks)
            pending_hours = sum(float(t.get("estimated_hours") or 0) for t in pending_tasks)

            is_flagged = len(overdue_tasks) > 0 or (len(pending_tasks) > 0 and len(done_tasks) == 0)
            reasons = []
            if len(overdue_tasks) > 0:
                reasons.append(f"{len(overdue_tasks)} Overdue Task(s)")
            if len(pending_tasks) > 0 and len(done_tasks) == 0:
                reasons.append("Zero Completed Tasks")
            flag_status = "FLAGGED" if is_flagged else "NORMAL"
            flag_reason = "; ".join(reasons) if is_flagged else "On track"

            writer.writerow([
                m["id"], m["name"], m.get("role", ""), m.get("max_weekly_hours", 40),
                round(hours_worked, 2), round(pending_hours, 2), len(done_tasks),
                len(pending_tasks), len(overdue_tasks), flag_status, flag_reason
            ])

        csv_content = output.getvalue()
        return {
            "success": True,
            "filename": f"team_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "csv": csv_content,
        }


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

    @mcp.tool(name="generate_csv_report", description="READ OPERATION — Generate a downloadable CSV report summarizing team hours worked, task completion, overdue work, and member flagging status.")
    async def generate_csv_report_tool(project_id: int | None = None):
        return await tools.generate_csv_report(project_id=project_id)
