"""
Planning tools — all AI-powered via Groq.

generate_project_plan  → full structured plan (milestones, tasks, risks, recommendations)
recommend_project_roles → role assignments matched against real team data
generate_subtasks       → smart task breakdown with estimates and dependencies
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pm_mcp.ai.groq_client import ask_groq, ask_groq_json
from pm_mcp.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PlanningTools:
    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    # ── Project plan ──────────────────────────────────────────────────────────

    async def generate_project_plan(
        self,
        *,
        project_description: str,
        objectives: str | None = None,
        deadline: str | None = None,
        team_information: str | None = None,
        technology: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Ask Groq to produce a full project plan as structured JSON."""
        context = f"Project description: {project_description}"
        if objectives:
            context += f"\nObjectives: {objectives}"
        if deadline:
            context += f"\nDeadline: {deadline}"
        if technology:
            context += f"\nTechnology: {technology}"
        if domain:
            context += f"\nDomain: {domain}"
        if team_information:
            context += f"\nTeam: {team_information}"

        prompt = f"""
You are a senior project manager. Given the following project context, produce a detailed project plan as JSON.

{context}

Return ONLY a JSON object with this exact structure (no markdown fences):
{{
  "project": {{
    "name": "...",
    "description": "...",
    "deadline": "...",
    "technology": "...",
    "domain": "..."
  }},
  "milestones": [
    {{"name": "...", "status": "PLANNED", "description": "..."}}
  ],
  "tasks": [
    {{
      "id": 1,
      "title": "...",
      "description": "...",
      "estimated_hours": 8,
      "priority": "HIGH",
      "dependencies": [],
      "role": "..."
    }}
  ],
  "risks": [
    {{"type": "SCHEDULE|RESOURCE|TECHNICAL", "severity": "HIGH|MEDIUM|LOW", "description": "..."}}
  ],
  "recommendations": [
    {{"title": "...", "detail": "..."}}
  ]
}}

Generate 4-8 realistic tasks with accurate dependencies and hour estimates.
""".strip()

        try:
            plan = await ask_groq_json(prompt)
            plan["ai_generated"] = True
            return plan
        except Exception as exc:
            logger.warning("Groq plan generation failed: %s — using fallback", exc)
            return _fallback_plan(project_description, deadline, technology, domain)

    # ── Role recommendations ──────────────────────────────────────────────────

    async def recommend_project_roles(
        self,
        *,
        project_description: str,
        project_type: str,
        objectives: str | None = None,
        team_members: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Ask Groq which team members best fit each required role."""
        members = team_members or await self.repository.list_team_members()
        members_summary = json.dumps(
            [{"id": m["id"], "name": m["name"], "role": m.get("role"), "skills": m.get("skills", [])}
             for m in members],
            indent=2,
        )

        prompt = f"""
You are a staffing advisor. Given the project and team below, recommend role assignments.

Project type: {project_type}
Project description: {project_description}
{"Objectives: " + objectives if objectives else ""}

Available team members:
{members_summary}

Return ONLY a JSON object (no markdown fences):
{{
  "success": true,
  "project_type": "{project_type}",
  "roles": [
    {{
      "role": "...",
      "responsibilities": ["..."],
      "required_skills": ["..."],
      "estimated_involvement": "30%",
      "suitable_team_members": ["Alice", "Bob"],
      "reasoning": "..."
    }}
  ]
}}
""".strip()

        try:
            result = await ask_groq_json(prompt)
            result["ai_generated"] = True
            return result
        except Exception as exc:
            logger.warning("Groq role recommendation failed: %s — using fallback", exc)
            return _fallback_roles(project_type, members)

    # ── Subtask generation ────────────────────────────────────────────────────

    async def generate_subtasks(
        self,
        *,
        task_title: str,
        description: str | None = None,
        project_context: str | None = None,
    ) -> dict[str, Any]:
        """Ask Groq to break a task into concrete, actionable subtasks."""
        context = f"Task: {task_title}"
        if description:
            context += f"\nDescription: {description}"
        if project_context:
            context += f"\nProject context: {project_context}"

        prompt = f"""
You are a senior engineering lead. Break the following task into clear, actionable subtasks.

{context}

Return ONLY a JSON object (no markdown fences):
{{
  "success": true,
  "subtasks": [
    {{
      "id": 1,
      "title": "...",
      "description": "...",
      "estimated_hours": 3,
      "priority": "HIGH",
      "dependencies": [],
      "suggested_role": "Backend Developer"
    }}
  ]
}}

Generate 3-6 subtasks. Each must have realistic hour estimates and dependency IDs.
""".strip()

        try:
            result = await ask_groq_json(prompt)
            result["ai_generated"] = True
            return result
        except Exception as exc:
            logger.warning("Groq subtask generation failed: %s — using fallback", exc)
            return _fallback_subtasks(task_title, description)


# ── Static fallbacks (used when Groq is unavailable) ─────────────────────────

def _fallback_plan(description: str, deadline: str | None, technology: str | None, domain: str | None) -> dict[str, Any]:
    return {
        "project": {"name": "Generated project", "description": description, "deadline": deadline, "technology": technology, "domain": domain},
        "milestones": [
            {"name": "Discovery and Scope", "status": "PLANNED", "description": "Requirements and kickoff"},
            {"name": "Implementation Sprint", "status": "PLANNED", "description": "Core build"},
            {"name": "QA and Launch", "status": "PLANNED", "description": "Testing and release"},
        ],
        "tasks": [
            {"id": 1, "title": "Project kickoff and requirements", "description": description, "estimated_hours": 12, "priority": "HIGH", "dependencies": [], "role": "Project Manager"},
            {"id": 2, "title": "Core feature implementation", "description": "Build primary features.", "estimated_hours": 32, "priority": "HIGH", "dependencies": [1], "role": "Backend Developer"},
            {"id": 3, "title": "Frontend experience", "description": "Build UI.", "estimated_hours": 24, "priority": "HIGH", "dependencies": [1], "role": "Frontend Developer"},
            {"id": 4, "title": "QA and testing", "description": "Validate quality.", "estimated_hours": 16, "priority": "MEDIUM", "dependencies": [2, 3], "role": "QA Engineer"},
        ],
        "risks": [{"type": "SCHEDULE", "severity": "MEDIUM", "description": "Delivery date is tight."}],
        "recommendations": [{"title": "Start with sprint planning", "detail": "Review dependency ordering."}],
        "ai_generated": False,
    }


def _fallback_roles(project_type: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    def match(skills_needed):
        return [m["name"] for m in members if any(s in (m.get("skills") or []) for s in skills_needed)]
    return {
        "success": True,
        "project_type": project_type,
        "roles": [
            {"role": "Project Manager", "responsibilities": ["Scope", "Stakeholders"], "required_skills": ["planning"], "estimated_involvement": "20%", "suitable_team_members": match(["planning"])},
            {"role": "Backend Developer", "responsibilities": ["API", "Data"], "required_skills": ["python", "api"], "estimated_involvement": "35%", "suitable_team_members": match(["python", "api"])},
            {"role": "Frontend Developer", "responsibilities": ["UI"], "required_skills": ["react"], "estimated_involvement": "30%", "suitable_team_members": match(["react"])},
            {"role": "QA Engineer", "responsibilities": ["Testing"], "required_skills": ["testing"], "estimated_involvement": "15%", "suitable_team_members": match(["testing"])},
        ],
        "ai_generated": False,
    }


def _fallback_subtasks(task_title: str, description: str | None) -> dict[str, Any]:
    return {
        "success": True,
        "subtasks": [
            {"id": 1, "title": f"Analyze {task_title}", "description": description or "Inspect requirements.", "estimated_hours": 3, "priority": "HIGH", "dependencies": [], "suggested_role": "Project Manager"},
            {"id": 2, "title": f"Implement {task_title}", "description": "Build the deliverable.", "estimated_hours": 8, "priority": "HIGH", "dependencies": [1], "suggested_role": "Backend Developer"},
            {"id": 3, "title": f"Validate {task_title}", "description": "Check acceptance criteria.", "estimated_hours": 4, "priority": "MEDIUM", "dependencies": [2], "suggested_role": "QA Engineer"},
        ],
        "ai_generated": False,
    }


def register_planning_tools(mcp, repository):
    tools = PlanningTools(repository)

    @mcp.tool(name="generate_project_plan", description="AI OPERATION — Use Groq to generate a full project plan with milestones, tasks, risk analysis, and recommendations based on your project description.")
    async def generate_project_plan_tool(project_description: str, objectives: str | None = None, deadline: str | None = None, team_information: str | None = None, technology: str | None = None, domain: str | None = None):
        return await tools.generate_project_plan(project_description=project_description, objectives=objectives, deadline=deadline, team_information=team_information, technology=technology, domain=domain)

    @mcp.tool(name="recommend_project_roles", description="AI OPERATION — Use Groq to recommend which team members best fit each project role based on skills and project type.")
    async def recommend_project_roles_tool(project_description: str, project_type: str, objectives: str | None = None, team_members: list[dict[str, Any]] | None = None):
        return await tools.recommend_project_roles(project_description=project_description, project_type=project_type, objectives=objectives, team_members=team_members)

    @mcp.tool(name="generate_subtasks", description="AI OPERATION — Use Groq to break a task into concrete subtasks with time estimates, dependencies, and role suggestions.")
    async def generate_subtasks_tool(task_title: str, description: str | None = None, project_context: str | None = None):
        return await tools.generate_subtasks(task_title=task_title, description=description, project_context=project_context)
