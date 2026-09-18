import asyncio

import pytest

from pm_mcp.repositories.mock_repository import MockRepository
from pm_mcp.tools.projects import ProjectTools
from pm_mcp.tools.tasks import TaskTools
from pm_mcp.tools.team import TeamTools
from pm_mcp.tools.assignment import AssignmentTools
from pm_mcp.tools.analytics import AnalyticsTools
from pm_mcp.engines.assignment_engine import AssignmentEngine
from pm_mcp.engines.dependency_engine import DependencyEngine
from pm_mcp.engines.duplicate_engine import DuplicateEngine
from pm_mcp.engines.schedule_engine import ScheduleEngine
from pm_mcp.engines.risk_engine import RiskEngine
from pm_mcp.engines.workload_engine import WorkloadEngine
import pm_mcp.server as server_module


@pytest.fixture
def repo():
    return MockRepository()


@pytest.mark.asyncio
async def test_project_creation(repo):
    tools = ProjectTools(repo)
    result = await tools.create_project(name="Website Redesign", description="Modernize website", priority="HIGH", owner_id=1)
    assert result["success"] is True
    assert result["project"]["name"] == "Website Redesign"


@pytest.mark.asyncio
async def test_project_creation_generates_description_when_missing(repo):
    tools = ProjectTools(repo)
    result = await tools.create_project(name="Mobile App Launch", priority="HIGH", owner_id=1)
    assert result["success"] is True
    assert "mobile app launch" in result["project"]["description"].lower()
    assert len(result["project"]["description"]) > 20


@pytest.mark.asyncio
async def test_task_creation_and_assignment(repo):
    tools = TaskTools(repo)
    task = await tools.create_task(project_id=1, title="Build API", priority="HIGH", estimated_hours=8, assignee_id=2)
    assert task["success"] is True
    assert task["task"]["title"] == "Build API"

    assign = AssignmentTools(repo)
    updated = await assign.assign_task(task_id=task["task"]["id"], member_id=5)
    assert updated["success"] is True
    assert updated["task"]["assignee_id"] == 5


@pytest.mark.asyncio
async def test_workload_calculation(repo):
    members = await repo.list_team_members()
    tasks = await repo.list_tasks(project_id=1)
    summary = WorkloadEngine.summarize_workload(members, tasks)
    assert "members" in summary
    assert isinstance(summary["members"], list)
    assert summary["members"][0]["member_id"] == 1


@pytest.mark.asyncio
async def test_skill_matching(repo):
    task = {"title": "Build auth API", "description": "Add login API endpoints", "estimated_hours": 12, "required_skills": ["python", "api"], "due_date": "2026-10-01"}
    members = await repo.list_team_members()
    recommendation = AssignmentEngine().recommend_assignee(task=task, team_members=members, project={"team_members": members})
    assert recommendation["recommended_member"] is not None
    assert recommendation["score"] >= 0


@pytest.mark.asyncio
async def test_dependency_detection(repo):
    tasks = await repo.list_tasks(project_id=1)
    result = DependencyEngine.analyze(1, tasks)
    assert "blocked_tasks" in result
    assert isinstance(result["blocked_tasks"], list)


@pytest.mark.asyncio
async def test_risk_detection(repo):
    project = await repo.get_project(1)
    tasks = await repo.list_tasks(project_id=1)
    members = await repo.list_team_members()
    result = RiskEngine.analyze(1, project, tasks, members)
    assert "risks" in result
    assert isinstance(result["risks"], list)


@pytest.mark.asyncio
async def test_duplicate_detection(repo):
    tasks = await repo.list_tasks(project_id=1)
    duplicates = DuplicateEngine.detect(1, tasks)
    assert isinstance(duplicates, list)


@pytest.mark.asyncio
async def test_schedule_analysis(repo):
    project = await repo.get_project(1)
    tasks = await repo.list_tasks(project_id=1)
    members = await repo.list_team_members()
    result = ScheduleEngine.analyze(1, project, tasks, members)
    assert result["status"] in {"feasible", "at_risk", "infeasible"}


@pytest.mark.asyncio
async def test_dry_run_assignment(repo):
    assign = AssignmentTools(repo)
    result = await assign.auto_assign_project(project_id=1, dry_run=True)
    assert result["success"] is True
    assert result["dry_run"] is True


@pytest.mark.asyncio
async def test_api_errors_and_missing_data(repo):
    tools = ProjectTools(repo)
    missing = await tools.get_project(project_id=999)
    assert missing["success"] is False
    assert missing["error"]["code"] == "PROJECT_NOT_FOUND"

    task_tools = TaskTools(repo)
    missing_task = await task_tools.get_task(task_id=999)
    assert missing_task["success"] is False
    assert missing_task["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_invalid_input(repo):
    task_tools = TaskTools(repo)
    result = await task_tools.update_task(task_id=1)
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_mcp_tool_registration():
    tools = await server_module.mcp.list_tools()
    names = {tool.name for tool in tools}
    assert "create_project" in names
    assert "create_task" in names
    assert "assign_task" in names
    assert "analyze_project_risks" in names
