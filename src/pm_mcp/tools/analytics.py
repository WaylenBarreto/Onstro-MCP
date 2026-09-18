from __future__ import annotations

from typing import Any

from pm_mcp.api.pm_client import PMApiClientError
from pm_mcp.config import get_app_settings
from pm_mcp.engines.dependency_engine import DependencyEngine
from pm_mcp.engines.duplicate_engine import DuplicateEngine
from pm_mcp.engines.risk_engine import RiskEngine
from pm_mcp.engines.schedule_engine import ScheduleEngine
from pm_mcp.engines.workload_engine import WorkloadEngine
from pm_mcp.repositories.mock_repository import MockRepository


class AnalyticsTools:
    def __init__(self, repository: MockRepository | None = None):
        self.repository = repository
        self.settings = get_app_settings()

    async def analyze_dependencies(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            project = await self.repository.get_project(project_id)
            tasks = await self.repository.list_tasks(project_id=project_id)
            return {"success": True, **DependencyEngine.analyze(project_id, tasks)}
        return {"success": True, "message": "Not implemented for remote API mode"}

    async def analyze_project_risks(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            project = await self.repository.get_project(project_id)
            tasks = await self.repository.list_tasks(project_id=project_id)
            members = await self.repository.list_team_members()
            return {"success": True, **RiskEngine.analyze(project_id, project, tasks, members)}
        return {"success": True, "message": "Not implemented for remote API mode"}

    async def analyze_team_workload(self, *, project_id: int | None = None, team: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if self.settings.mock_mode:
            members = await self.repository.list_team_members()
            tasks = await self.repository.list_tasks(project_id=project_id)
            summary = WorkloadEngine.summarize_workload(members, tasks)
            return {"success": True, **summary}
        return {"success": True, "message": "Not implemented for remote API mode"}

    async def rebalance_project_workload(self, *, project_id: int, dry_run: bool = True) -> dict[str, Any]:
        tasks = await self.repository.list_tasks(project_id=project_id)
        members = await self.repository.list_team_members()
        overloaded = [member for member in members if any(task.get("assignee_id") == member["id"] for task in tasks)]
        proposals = []
        if dry_run:
            return {"success": True, "dry_run": True, "project_id": project_id, "recommendations": proposals, "overloaded_members": [m["id"] for m in overloaded]}
        return {"success": True, "dry_run": False, "project_id": project_id, "recommendations": proposals}

    async def analyze_schedule(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            project = await self.repository.get_project(project_id)
            tasks = await self.repository.list_tasks(project_id=project_id)
            members = await self.repository.list_team_members()
            return {"success": True, **ScheduleEngine.analyze(project_id, project, tasks, members)}
        return {"success": True, "message": "Not implemented for remote API mode"}

    async def detect_duplicate_tasks(self, *, project_id: int) -> dict[str, Any]:
        if self.settings.mock_mode:
            tasks = await self.repository.list_tasks(project_id=project_id)
            return {"success": True, "duplicates": DuplicateEngine.detect(project_id, tasks)}
        return {"success": True, "message": "Not implemented for remote API mode"}


def register_analytics_tools(mcp, repository):
    tools = AnalyticsTools(repository)

    @mcp.tool(name="analyze_dependencies", description="READ OPERATION — Analyze dependencies, blockers, circular chains, and tasks that cannot start yet.")
    async def analyze_dependencies_tool(project_id: int):
        return await tools.analyze_dependencies(project_id=project_id)

    @mcp.tool(name="analyze_project_risks", description="READ OPERATION — Analyze project risks including overdue work, capacity issues, blockers, and unassigned tasks.")
    async def analyze_project_risks_tool(project_id: int):
        return await tools.analyze_project_risks(project_id=project_id)

    @mcp.tool(name="analyze_team_workload", description="READ OPERATION — Identify overloaded or underutilized members and summarize workload distribution.")
    async def analyze_team_workload_tool(project_id: int | None = None):
        return await tools.analyze_team_workload(project_id=project_id)

    @mcp.tool(name="rebalance_project_workload", description="WRITE OPERATION with dry_run support — Review overloaded members and propose reassignments without moving tasks until dry_run is false.")
    async def rebalance_project_workload_tool(project_id: int, dry_run: bool = True):
        return await tools.rebalance_project_workload(project_id=project_id, dry_run=dry_run)

    @mcp.tool(name="analyze_schedule", description="READ OPERATION — Evaluate schedule feasibility, remaining work, and deadline risk.")
    async def analyze_schedule_tool(project_id: int):
        return await tools.analyze_schedule(project_id=project_id)

    @mcp.tool(name="detect_duplicate_tasks", description="READ OPERATION — Find tasks with similar titles/descriptions and report likely duplicates without deleting anything.")
    async def detect_duplicate_tasks_tool(project_id: int):
        return await tools.detect_duplicate_tasks(project_id=project_id)
