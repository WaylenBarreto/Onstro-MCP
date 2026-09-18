from __future__ import annotations

import math
from datetime import datetime
from typing import Any


class AssignmentEngine:
    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or {
            "skill_match": 0.40,
            "role_match": 0.20,
            "workload": 0.15,
            "availability": 0.10,
            "deadline_feasibility": 0.10,
            "project_context": 0.05,
        }

    def recommend_assignee(
        self,
        *,
        task: dict[str, Any],
        team_members: list[dict[str, Any]],
        project: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task_title = (task.get("title") or "").lower()
        task_desc = (task.get("description") or "").lower()
        required_skills = set((task.get("required_skills") or []) if isinstance(task.get("required_skills"), list) else [])
        task_deadline = task.get("due_date")

        candidates = []
        for member in team_members:
            skills = {s.lower() for s in member.get("skills", [])}
            role = (member.get("role") or "").lower()
            workload = float(member.get("current_workload", 0) or 0)
            max_hours = float(member.get("max_weekly_hours", 40) or 40)
            availability = float(member.get("availability", 1.0) or 1.0)
            utilization = (workload / max_hours) if max_hours else 0.0

            skill_score = 0.0
            if required_skills:
                overlap = len(required_skills.intersection(skills))
                skill_score = overlap / max(len(required_skills), 1)
            else:
                skill_score = 0.5 if any(token in task_title or token in task_desc for token in ("api", "ui", "qa", "frontend", "backend", "design")) else 0.3

            role_score = 0.5
            if "backend" in role and any(token in task_title + " " + task_desc for token in ["api", "backend", "database", "server"]):
                role_score = 1.0
            if "frontend" in role and any(token in task_title + " " + task_desc for token in ["ui", "frontend", "design", "page", "component"]):
                role_score = 1.0
            if "qa" in role and any(token in task_title + " " + task_desc for token in ["test", "qa", "validation", "regression"]):
                role_score = 1.0
            if "project manager" in role and any(token in task_title + " " + task_desc for token in ["plan", "risk", "deliverable", "scope"]):
                role_score = 1.0

            workload_score = max(0.0, 1.0 - utilization)
            availability_score = float(availability)
            deadline_score = 1.0
            if task_deadline:
                try:
                    if isinstance(task_deadline, str):
                        due = datetime.fromisoformat(task_deadline)
                        deadline_score = max(0.0, 1.0 - ((due - datetime.now()).days / 30.0))
                        deadline_score = min(1.0, max(0.1, deadline_score))
                except ValueError:
                    deadline_score = 1.0

            project_context_score = 0.5
            if project:
                project_members = [m.get("id") for m in project.get("team_members", [])]
                if member.get("id") in project_members:
                    project_context_score = 1.0

            total = (
                self.weights["skill_match"] * skill_score
                + self.weights["role_match"] * role_score
                + self.weights["workload"] * workload_score
                + self.weights["availability"] * availability_score
                + self.weights["deadline_feasibility"] * deadline_score
                + self.weights["project_context"] * project_context_score
            )

            reasons = []
            if skill_score >= 0.6:
                reasons.append("Strong skill alignment")
            if role_score >= 0.8:
                reasons.append("Role is a good fit")
            if workload_score < 0.5:
                reasons.append("Current workload is manageable")
            if availability_score >= 0.8:
                reasons.append("High availability")
            if deadline_score > 0.7:
                reasons.append("Deadline is feasible")
            if project_context_score > 0.8:
                reasons.append("Already engaged in the project")

            candidates.append({
                "member": member,
                "score": round(total, 4),
                "reasons": reasons or ["No strong signal, but candidate is available"],
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        best = candidates[0] if candidates else None
        alt = candidates[1:4]
        return {
            "recommended_member": best["member"] if best else None,
            "score": best["score"] if best else 0.0,
            "alternative_candidates": [{"member": c["member"], "score": c["score"]} for c in alt],
            "reasons": best["reasons"] if best else [],
            "workload_impact": {
                "assigned_hours": float((best["member"].get("current_workload", 0) if best else 0) + (task.get("estimated_hours", 0) or 0)),
                "available_hours": float((best["member"].get("max_weekly_hours", 40) if best else 0) * (best["member"].get("availability", 1.0) if best else 1.0)),
            },
            "potential_risks": [
                "If the member is overloaded, delivery risk increases.",
                "If the deadline is imminent, dependency delays may affect completion.",
            ] if best else [],
        }
