from __future__ import annotations

from typing import Any

from pm_mcp.api.pm_client import PMApiClientError
from pm_mcp.config import get_app_settings
from pm_mcp.repositories.mock_repository import MockRepository


class PlanningTools:
    def __init__(self, repository: MockRepository | None = None):
        self.repository = repository
        self.settings = get_app_settings()

    async def generate_project_plan(self, *, project_description: str, objectives: str | None = None, deadline: str | None = None, team_information: str | None = None, technology: str | None = None, domain: str | None = None) -> dict[str, Any]:
        milestone_names = [
            "Discovery and Scope",
            "Design and Architecture",
            "Implementation Sprint",
            "QA and Launch",
        ]
        tasks = [
            {"title": "Project kickoff and requirements", "description": project_description, "estimated_hours": 12, "priority": "HIGH", "dependencies": [], "role": "Project Manager"},
            {"title": "Core feature implementation", "description": objectives or "Build the core product experience.", "estimated_hours": 32, "priority": "HIGH", "dependencies": [1], "role": "Backend Developer"},
            {"title": "Frontend experience", "description": "Create the user interface and interactions.", "estimated_hours": 24, "priority": "HIGH", "dependencies": [1], "role": "Frontend Developer"},
            {"title": "QA and testing", "description": "Validate quality and performance.", "estimated_hours": 16, "priority": "MEDIUM", "dependencies": [2, 3], "role": "QA Engineer"},
        ]
        return {
            "project": {"name": "Generated project", "description": project_description, "deadline": deadline, "technology": technology, "domain": domain},
            "milestones": [{"name": name, "status": "PLANNED"} for name in milestone_names],
            "tasks": tasks,
            "dependencies": [{"task": 2, "depends_on": 1}, {"task": 3, "depends_on": 1}, {"task": 4, "depends_on": 2}, {"task": 4, "depends_on": 3}],
            "risks": [{"type": "SCHEDULE", "severity": "MEDIUM", "description": "Delivery date is tight and dependencies will need active coordination."}],
            "recommendations": [{"title": "Start with sprint planning", "detail": "Review dependency ordering and assign work before build starts."}],
        }

    async def recommend_project_roles(self, *, project_description: str, project_type: str, objectives: str | None = None, team_members: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        members = team_members or []
        roles = [
            {"role": "Project Manager", "responsibilities": ["Scope management", "Stakeholder alignment"], "required_skills": ["planning", "communication"], "estimated_involvement": "20%", "suitable_team_members": [m["name"] for m in members if "planning" in (m.get("skills") or []) or m.get("role") == "Project Manager"]},
            {"role": "Backend Developer", "responsibilities": ["API and data flows"], "required_skills": ["api", "python", "database"], "estimated_involvement": "35%", "suitable_team_members": [m["name"] for m in members if "api" in (m.get("skills") or []) or "python" in (m.get("skills") or [])]},
            {"role": "Frontend Developer", "responsibilities": ["UX flows and page implementations"], "required_skills": ["react", "javascript"], "estimated_involvement": "30%", "suitable_team_members": [m["name"] for m in members if "react" in (m.get("skills") or []) or "javascript" in (m.get("skills") or [])]},
            {"role": "QA Engineer", "responsibilities": ["Testing and regression"], "required_skills": ["testing", "automation"], "estimated_involvement": "15%", "suitable_team_members": [m["name"] for m in members if "testing" in (m.get("skills") or []) or m.get("role") == "QA Engineer"]},
        ]
        return {"success": True, "project_type": project_type, "roles": roles}

    async def generate_subtasks(self, *, task_title: str, description: str | None = None, project_context: str | None = None) -> dict[str, Any]:
        return {
            "success": True,
            "subtasks": [
                {"title": f"Analyze {task_title}", "description": description or "Inspect requirements and expected outcome.", "estimated_hours": 3, "priority": "HIGH", "dependencies": [], "suggested_role": "Project Manager"},
                {"title": f"Implement {task_title}", "description": "Build the primary deliverable.", "estimated_hours": 8, "priority": "HIGH", "dependencies": [1], "suggested_role": "Backend Developer"},
                {"title": f"Validate {task_title}", "description": "Check quality and ensure acceptance criteria are met.", "estimated_hours": 4, "priority": "MEDIUM", "dependencies": [2], "suggested_role": "QA Engineer"},
            ],
        }


def register_planning_tools(mcp, repository):
    tools = PlanningTools(repository)

    @mcp.tool(name="generate_project_plan", description="READ/PLANNING OPERATION — Generate a structured project plan including milestones, tasks, dependencies, and risks. This returns structured JSON output and does not modify project data by itself.")
    async def generate_project_plan_tool(project_description: str, objectives: str | None = None, deadline: str | None = None, team_information: str | None = None, technology: str | None = None, domain: str | None = None):
        return await tools.generate_project_plan(project_description=project_description, objectives=objectives, deadline=deadline, team_information=team_information, technology=technology, domain=domain)

    @mcp.tool(name="recommend_project_roles", description="READ OPERATION — Recommend project roles based on team skills and project objectives. Do not invent team members; only use available team data.")
    async def recommend_project_roles_tool(project_description: str, project_type: str, objectives: str | None = None, team_members: list[dict[str, Any]] | None = None):
        return await tools.recommend_project_roles(project_description=project_description, project_type=project_type, objectives=objectives, team_members=team_members)

    @mcp.tool(name="generate_subtasks", description="READ/PLANNING OPERATION — Break a task into clear, structured subtasks with estimate, dependencies, and suggested role. This does not modify data.")
    async def generate_subtasks_tool(task_title: str, description: str | None = None, project_context: str | None = None):
        return await tools.generate_subtasks(task_title=task_title, description=description, project_context=project_context)
