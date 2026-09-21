"""
UI Server — FastAPI backend for the Onstro MCP web UI.

Talks directly to SqliteRepository (or MockRepository in test mode) instead
of spawning an MCP subprocess. This avoids the JSON-RPC handshake complexity
while sharing the exact same data layer the MCP server uses.
"""
import os
import sys

# Ensure src/ is on the path when running directly with `py ui_server.py`
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pm_mcp.config import get_settings
from pm_mcp.repositories.mock_repository import MockRepository
from pm_mcp.repositories.sqlite_repository import SqliteRepository
from pm_mcp.tools.projects import ProjectTools
from pm_mcp.tools.tasks import TaskTools
from pm_mcp.tools.team import TeamTools
from pm_mcp.tools.insights import InsightsTools


import logging

logger = logging.getLogger("ui_server")


# ── Repository selection ──────────────────────────────────────────────────────

def _make_repository():
    settings = get_settings()
    if settings.mock_mode:
        return MockRepository()
    return SqliteRepository()


# ── FastAPI lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = _make_repository()
    app.state.repo = repo
    app.state.projects = ProjectTools(repo)
    app.state.tasks = TaskTools(repo)
    app.state.team = TeamTools(repo)
    app.state.insights = InsightsTools(repo)
    yield
    # cleanup
    if hasattr(repo, "close"):
        try:
            repo.close()
        except Exception:
            pass
    elif hasattr(repo, "_conn") and repo._conn:
        try:
            repo._conn.close()
        except Exception:
            pass
    app.state.repo = None
    app.state.projects = None
    app.state.tasks = None
    app.state.team = None
    app.state.insights = None


app = FastAPI(title="Onstro Project Management Platform", lifespan=lifespan)


# ── Helper ────────────────────────────────────────────────────────────────────

def _tools(request) -> tuple[ProjectTools, TaskTools, TeamTools, InsightsTools]:
    app = request.app
    repo = getattr(app.state, "repo", None)
    if repo is None or getattr(app.state, "projects", None) is None:
        repo = _make_repository()
        app.state.repo = repo
        app.state.projects = ProjectTools(repo)
        app.state.tasks = TaskTools(repo)
        app.state.team = TeamTools(repo)
        app.state.insights = InsightsTools(repo)
    return (
        app.state.projects,
        app.state.tasks,
        app.state.team,
        app.state.insights,
    )


# ── Members ───────────────────────────────────────────────────────────────────

from fastapi import Request

@app.get("/api/members")
async def get_members(request: Request):
    try:
        _, _, team, _ = _tools(request)
        result = await team.list_team_members()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", {}).get("message", "Failed to get members"))
        return {"members": result.get("members", [])}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/members")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Projects ──────────────────────────────────────────────────────────────────

@app.get("/api/projects")
async def get_projects(request: Request):
    try:
        projects_tool, _, _, _ = _tools(request)
        result = await projects_tool.list_projects()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", {}).get("message", "Failed to get projects"))
        return {"projects": result.get("projects", [])}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/projects")
        raise HTTPException(status_code=500, detail=str(exc))


class EnhanceProjectRequest(BaseModel):
    title: str
    description: str = ""


@app.post("/api/ai/enhance-project")
async def enhance_project(req: EnhanceProjectRequest, request: Request):
    try:
        projects_tool, _, _, _ = _tools(request)
        result = await projects_tool.enhance_project(title=req.title, description=req.description)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in POST /api/ai/enhance-project")
        raise HTTPException(status_code=500, detail=str(exc))



class CreateProjectRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "MEDIUM"


@app.post("/api/projects/create")
async def create_project(req: CreateProjectRequest, request: Request):
    try:
        projects_tool, _, _, _ = _tools(request)
        result = await projects_tool.create_project(
            name=req.title,
            description=req.description if req.description else None,
            priority=req.priority,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", {}).get("message", "Failed to create project"),
            )
        project = result.get("project", {})
        return {
            "success": True,
            "original": {"title": req.title, "description": req.description},
            "mcp_modified": {
                "title": project.get("name", ""),
                "description": project.get("description", ""),
            },
            "project": project,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in POST /api/projects/create")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.get("/api/projects/{project_id}/tasks")
async def get_tasks(project_id: int, request: Request):
    try:
        _, tasks_tool, _, _ = _tools(request)
        result = await tasks_tool.list_tasks(project_id=project_id)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", {}).get("message", "Failed to get tasks"))
        return {"tasks": result.get("tasks", [])}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/projects/{project_id}/tasks")
        raise HTTPException(status_code=500, detail=str(exc))


class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "MEDIUM"
    estimated_hours: float | None = None
    due_date: str | None = None
    assignee_id: int | None = None


@app.post("/api/projects/{project_id}/tasks")
async def create_task(project_id: int, req: CreateTaskRequest, request: Request):
    try:
        _, tasks_tool, _, _ = _tools(request)
        result = await tasks_tool.create_task(
            project_id=project_id,
            title=req.title,
            description=req.description or None,
            priority=req.priority,
            estimated_hours=req.estimated_hours,
            due_date=req.due_date,
            assignee_id=req.assignee_id,
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", {}).get("message", "Failed to create task"))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in POST /api/projects/{project_id}/tasks")
        raise HTTPException(status_code=500, detail=str(exc))


class LogTimeRequest(BaseModel):
    member_id: int
    hours_logged: float
    description: str = ""


@app.post("/api/tasks/{task_id}/log-time")
async def log_task_time(task_id: int, req: LogTimeRequest, request: Request):
    try:
        _, tasks_tool, _, _ = _tools(request)
        result = await tasks_tool.log_time(
            task_id=task_id,
            member_id=req.member_id,
            hours_logged=req.hours_logged,
            description=req.description or None,
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", {}).get("message", "Failed to log time"))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in POST /api/tasks/{task_id}/log-time")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/time-logs")
async def get_time_logs(request: Request, task_id: int | None = None, member_id: int | None = None):
    try:
        _, tasks_tool, _, _ = _tools(request)
        result = await tasks_tool.get_time_logs(task_id=task_id, member_id=member_id)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", {}).get("message", "Failed to get time logs"))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/time-logs")
        raise HTTPException(status_code=500, detail=str(exc))



# ── Insights ──────────────────────────────────────────────────────────────────

@app.get("/api/insights/member/{member_id}")
async def get_member_insights(member_id: int, request: Request):
    try:
        _, _, _, insights_tool = _tools(request)
        result = await insights_tool.get_member_insights(member_id=member_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/insights/member/{member_id}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/insights/project/{project_id}")
async def get_project_insights(project_id: int, request: Request):
    try:
        _, _, _, insights_tool = _tools(request)
        result = await insights_tool.get_project_insights(project_id=project_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/insights/project/{project_id}")
        raise HTTPException(status_code=500, detail=str(exc))


from fastapi.responses import Response


@app.get("/api/reports/csv")
@app.get("/api/reports/team/csv")
async def download_team_csv(request: Request):
    try:
        from pm_mcp.tools.reporting import ReportingTools
        repo = getattr(request.app.state, "repo", None) or _make_repository()
        reporting = ReportingTools(repo)
        result = await reporting.generate_csv_report()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to generate CSV")
        filename = result.get("filename", "team_report.csv")
        return Response(
            content=result["csv"],
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/reports/csv")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/reports/project/{project_id}/csv")
async def download_project_csv(project_id: int, request: Request):
    try:
        from pm_mcp.tools.reporting import ReportingTools
        repo = getattr(request.app.state, "repo", None) or _make_repository()
        reporting = ReportingTools(repo)
        result = await reporting.generate_csv_report(project_id=project_id)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to generate CSV")
        filename = result.get("filename", f"project_{project_id}_report.csv")
        return Response(
            content=result["csv"],
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in GET /api/reports/project/{project_id}/csv")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Static files (the browser UI) ────────────────────────────────────────────

ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_static")
os.makedirs(ui_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=ui_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ui_server:app", host="127.0.0.1", port=8000, reload=True)
