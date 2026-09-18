from __future__ import annotations

from datetime import datetime
from typing import Any


class RiskEngine:
    @staticmethod
    def analyze(project_id: int, project: dict[str, Any] | None, tasks: list[dict[str, Any]], team_members: list[dict[str, Any]]) -> dict[str, Any]:
        risks: list[dict[str, Any]] = []
        project_tasks = [task for task in tasks if task.get("project_id") == project_id]
        due = project.get("due_date") if project else None

        overdue = [task["id"] for task in project_tasks if task.get("status") not in {"DONE", "CANCELLED"} and task.get("due_date") and task["due_date"] < datetime.now().strftime("%Y-%m-%d")]
        if overdue:
            risks.append({
                "type": "OVERDUE_TASKS",
                "severity": "HIGH",
                "description": "Tasks are overdue and may threaten the delivery date.",
                "affected_tasks": overdue,
                "recommended_action": "Prioritize overdue tasks and re-sequence dependencies.",
            })

        unassigned = [task["id"] for task in project_tasks if task.get("assignee_id") is None and task.get("status") != "DONE"]
        if unassigned:
            risks.append({
                "type": "UNASSIGNED_TASKS",
                "severity": "MEDIUM",
                "description": "Some tasks have no assigned owner.",
                "affected_tasks": unassigned,
                "recommended_action": "Assign owners using the recommendation engine before the next sprint.",
            })

        if due:
            try:
                deadline = datetime.fromisoformat(due)
                if (deadline - datetime.now()).days < 7:
                    risks.append({
                        "type": "IMMINENT_DEADLINE",
                        "severity": "HIGH",
                        "description": "The project deadline is close and capacity may be insufficient.",
                        "affected_tasks": [task["id"] for task in project_tasks],
                        "recommended_action": "Focus on critical tasks, remove non-essential scope, and increase capacity.",
                    })
            except ValueError:
                pass

        if any(task.get("status") == "BLOCKED" for task in project_tasks):
            blocked = [task["id"] for task in project_tasks if task.get("status") == "BLOCKED"]
            risks.append({
                "type": "BLOCKED_TASKS",
                "severity": "MEDIUM",
                "description": "Tasks are currently blocked by dependencies or waiting conditions.",
                "affected_tasks": blocked,
                "recommended_action": "Resolve blocker dependencies and confirm that requirements are complete.",
            })

        workload = sum(float(member.get("current_workload", 0) or 0) for member in team_members)
        if workload > 150:
            risks.append({
                "type": "WORKLOAD_PRESSURE",
                "severity": "MEDIUM",
                "description": "Combined team workload indicates visible delivery pressure.",
                "affected_tasks": [task["id"] for task in project_tasks],
                "recommended_action": "Redistribute tasks or add support for critical work.",
            })

        return {"risks": risks}
