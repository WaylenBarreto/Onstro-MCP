from __future__ import annotations

from datetime import datetime
from typing import Any


class ScheduleEngine:
    @staticmethod
    def analyze(project_id: int, project: dict[str, Any] | None, tasks: list[dict[str, Any]], team_members: list[dict[str, Any]]) -> dict[str, Any]:
        project_tasks = [task for task in tasks if task.get("project_id") == project_id]
        remaining = sum(float(task.get("estimated_hours", 0) or 0) for task in project_tasks if task.get("status") != "DONE")
        capacity = sum(float(member.get("max_weekly_hours", 40) or 40) * float(member.get("availability", 1.0) or 1.0) for member in team_members)
        due = project.get("due_date") if project else None
        status = "feasible"
        if due:
            try:
                days = (datetime.fromisoformat(due) - datetime.now()).days
                if remaining > capacity * max(days / 7.0, 1.0):
                    status = "at_risk"
                if days < 0:
                    status = "infeasible"
            except ValueError:
                pass
        critical = [task["id"] for task in project_tasks if task.get("priority") in {"HIGH", "CRITICAL"} and task.get("status") != "DONE"]
        return {
            "status": status,
            "remaining_work_hours": remaining,
            "available_capacity_hours": capacity,
            "deadline": due,
            "capacity_gap": max(0.0, remaining - capacity),
            "critical_tasks": critical,
            "recommended_changes": [
                "Reduce scope to critical features first.",
                "Reassign work to those with stronger skill match.",
            ],
        }
