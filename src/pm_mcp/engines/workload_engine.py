from __future__ import annotations

from typing import Any


class WorkloadEngine:
    @staticmethod
    def calculate_member_workload(member: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any]:
        assigned = [task for task in tasks if task.get("assignee_id") == member.get("id")]
        assigned_hours = sum(float(task.get("estimated_hours", 0) or 0) for task in assigned if task.get("status") != "DONE")
        max_hours = float(member.get("max_weekly_hours", 40) or 40)
        utilization = round((assigned_hours / max_hours) * 100, 2) if max_hours else 0.0
        overdue = sum(1 for task in assigned if task.get("status") not in ("DONE", "CANCELLED") and task.get("due_date"))
        return {
            "member_id": member.get("id"),
            "name": member.get("name"),
            "role": member.get("role"),
            "assigned_hours": assigned_hours,
            "maximum_hours": max_hours,
            "utilization_percentage": utilization,
            "active_task_count": len(assigned),
            "overdue_task_count": overdue,
        }

    @staticmethod
    def summarize_workload(team_members: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> dict[str, Any]:
        workloads = [WorkloadEngine.calculate_member_workload(member, tasks) for member in team_members]
        overloaded = [entry["member_id"] for entry in workloads if entry["utilization_percentage"] > 90]
        underutilized = [entry["member_id"] for entry in workloads if entry["utilization_percentage"] < 50]
        return {
            "members": workloads,
            "overloaded_members": overloaded,
            "underutilized_members": underutilized,
            "imbalance_score": round(float(sum(max(0.0, entry["utilization_percentage"] - 80) for entry in workloads)) / max(len(workloads), 1), 2),
        }
