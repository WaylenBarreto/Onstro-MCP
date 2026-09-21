from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from pm_mcp.ai.groq_client import ask_groq
from pm_mcp.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CreateProjectInput(BaseModel):
    name: str = Field(..., description="Project name")
    description: str | None = None
    priority: str = "MEDIUM"
    start_date: str | None = None
    due_date: str | None = None
    owner_id: int | None = None


class ProjectTools:
    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    @staticmethod
    def _fallback_description(name: str, priority: str | None = None, start_date: str | None = None, due_date: str | None = None) -> str:
        """Simple template used when Groq is unavailable."""
        clean_name = " ".join(str(name).strip().split()) or "Project initiative"
        base = f"Plan and deliver the {clean_name} initiative with clear scope, milestones, ownership, and measurable outcomes."
        if priority:
            base = f"{base} Priority: {priority}."
        date_bits = []
        if start_date:
            date_bits.append(f"start date {start_date}")
        if due_date:
            date_bits.append(f"due date {due_date}")
        if date_bits:
            base = f"{base} Timeline: {'; '.join(date_bits)}."
        return base

    @staticmethod
    async def _ai_description(name: str, priority: str | None = None, start_date: str | None = None, due_date: str | None = None) -> str:
        """Ask Groq to write a concise, professional project description."""
        context_parts = [f"Project name: {name}"]
        if priority:
            context_parts.append(f"Priority: {priority}")
        if start_date:
            context_parts.append(f"Start date: {start_date}")
        if due_date:
            context_parts.append(f"Due date: {due_date}")
        context = ", ".join(context_parts)
        prompt = (
            f"Write a concise (2-3 sentence) professional project description for the following: {context}. "
            "Include the goal, key deliverables, and expected outcome. Do not use bullet points."
        )
        desc = await ask_groq(prompt, max_tokens=200)
        return " ".join(desc.split())

    async def create_project(self, *, name: str, description: str | None = None, priority: str = "MEDIUM", start_date: str | None = None, due_date: str | None = None, owner_id: int | None = None) -> dict[str, Any]:
        normalized_description = description.strip() if isinstance(description, str) else description
        # MCP enrichment: emoji prefix + title-case
        name = f"\U0001f680 {name.title()}"
        if not normalized_description:
            try:
                raw_ai_desc = await self._ai_description(name=name, priority=priority, start_date=start_date, due_date=due_date)
                normalized_description = " ".join(raw_ai_desc.split())
            except Exception:
                normalized_description = self._fallback_description(name=name, priority=priority, start_date=start_date, due_date=due_date)
        else:
            normalized_description = f"{normalized_description}\n\n[MCP Note: Handled and processed by the Onstro AI Agent.]"
        payload = {
            "name": name,
            "description": normalized_description,
            "priority": priority,
            "start_date": start_date,
            "due_date": due_date,
            "owner_id": owner_id,
        }
        project = await self.repository.create_project(payload)
        return {"success": True, "project": project}

    async def get_project(self, *, project_id: int) -> dict[str, Any]:
        project = await self.repository.get_project(project_id)
        if not project:
            return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} was not found."}}
        return {"success": True, "project": project}

    async def list_projects(self, *, status: str | None = None, priority: str | None = None, owner_id: int | None = None) -> dict[str, Any]:
        projects = await self.repository.get_projects()
        if status:
            projects = [p for p in projects if p.get("status") == status]
        if priority:
            projects = [p for p in projects if p.get("priority") == priority]
        if owner_id is not None:
            projects = [p for p in projects if p.get("owner_id") == owner_id]
        return {"success": True, "projects": projects}

    async def update_project(self, *, project_id: int, **fields: Any) -> dict[str, Any]:
        allowed = {"name", "description", "status", "priority", "owner_id", "start_date", "due_date"}
        filtered = {k: v for k, v in fields.items() if v is not None and k in allowed}
        if not filtered:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": "No project fields were supplied for update."}}
        project = await self.repository.update_project(project_id, filtered)
        if not project:
            return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} was not found."}}
        return {"success": True, "project": project}

    async def delete_project(self, *, project_id: int) -> dict[str, Any]:
        deleted = await self.repository.delete_project(project_id)
        if not deleted:
            return {"success": False, "error": {"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} was not found."}}
        return {"success": True, "deleted": True, "project_id": project_id}

    async def enhance_project(self, *, title: str, description: str = "") -> dict[str, Any]:
        """Refine title & expand description using AI (Groq or fallback engine)."""
        clean_title = title.strip()
        clean_desc = description.strip()
        if not clean_title and not clean_desc:
            clean_title = "New Project Initiative"

        prompt = (
            f"You are an expert project management assistant.\n"
            f"User Supplied Title: {clean_title if clean_title else '(None)'}\n"
            f"User Supplied Description: {clean_desc if clean_desc else '(None)'}\n\n"
            f"Requirements:\n"
            f"1. Refine or generate a professional, clear, concise project title (title-cased, max 8-10 words).\n"
            f"2. If a description is provided, build directly upon the user's ideas and expand them in detail, specifying objectives, key deliverables, and scope. If no description is provided, generate a complete detailed project description based on the title.\n\n"
            f"Respond ONLY with valid JSON containing keys 'enhanced_title' and 'enhanced_description'. Do not include markdown fences."
        )
        try:
            from pm_mcp.ai.groq_client import ask_groq_json
            data = await ask_groq_json(prompt)
            enhanced_title = data.get("enhanced_title", clean_title)
            enhanced_desc = data.get("enhanced_description", clean_desc)
        except Exception as exc:
            logger.warning("Groq AI enhancement failed, using fallback: %s", exc)
            enhanced_title = (clean_title or "New Project Initiative").title()
            if clean_desc:
                enhanced_desc = f"{clean_desc}\n\nKey Objectives & Deliverables:\n• Detailed project plan & architecture.\n• Comprehensive implementation, QA testing, and rollout."
            else:
                enhanced_desc = f"Plan, design, and execute the {enhanced_title} project with defined milestones, clear ownership, and measurable deliverables."

        return {
            "success": True,
            "title": " ".join(str(enhanced_title).split()),
            "description": enhanced_desc,
        }


def register_project_tools(mcp, repository):
    tools = ProjectTools(repository)

    @mcp.tool(name="create_project", description="WRITE OPERATION — Create a new project. Use for startup planning or when the user asks to create a project. This modifies project data.")
    async def create_project_tool(name: str, description: str | None = None, priority: str = "MEDIUM", start_date: str | None = None, due_date: str | None = None, owner_id: int | None = None):
        return await tools.create_project(name=name, description=description, priority=priority, start_date=start_date, due_date=due_date, owner_id=owner_id)

    @mcp.tool(name="get_project", description="READ OPERATION — Retrieve a project's complete data.")
    async def get_project_tool(project_id: int):
        return await tools.get_project(project_id=project_id)

    @mcp.tool(name="list_projects", description="READ OPERATION — List projects with optional filters for status, priority, or owner_id.")
    async def list_projects_tool(status: str | None = None, priority: str | None = None, owner_id: int | None = None):
        return await tools.list_projects(status=status, priority=priority, owner_id=owner_id)

    @mcp.tool(name="update_project", description="WRITE OPERATION — Update only the supplied project fields.")
    async def update_project_tool(project_id: int, name: str | None = None, description: str | None = None, status: str | None = None, priority: str | None = None, owner_id: int | None = None, start_date: str | None = None, due_date: str | None = None):
        return await tools.update_project(project_id=project_id, name=name, description=description, status=status, priority=priority, owner_id=owner_id, start_date=start_date, due_date=due_date)

    @mcp.tool(name="delete_project", description="DESTRUCTIVE OPERATION — Permanently delete a project. Require explicit user confirmation before use.")
    async def delete_project_tool(project_id: int):
        return await tools.delete_project(project_id=project_id)

    @mcp.tool(name="enhance_project", description="AI OPERATION — Refine title and expand project description into a complete specification using AI.")
    async def enhance_project_tool(title: str, description: str = ""):
        return await tools.enhance_project(title=title, description=description)

