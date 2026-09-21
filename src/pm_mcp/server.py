from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

from pm_mcp.config import get_app_settings
from pm_mcp.logging_config import configure_logging
from pm_mcp.repositories.mock_repository import MockRepository
from pm_mcp.repositories.sqlite_repository import SqliteRepository
from pm_mcp.tools.projects import register_project_tools
from pm_mcp.tools.tasks import register_task_tools
from pm_mcp.tools.team import register_team_tools
from pm_mcp.tools.assignment import register_assignment_tools
from pm_mcp.tools.planning import register_planning_tools
from pm_mcp.tools.analytics import register_analytics_tools
from pm_mcp.tools.reporting import register_reporting_tools
from pm_mcp.tools.insights import register_insights_tools

configure_logging(get_app_settings().log_level)
logger = logging.getLogger(__name__)

mcp = MCPServer("pm-project-manager")
settings = get_app_settings()

# Use MockRepository only when explicitly in mock/test mode.
# Otherwise use the real SQLite-backed repository that persists data to disk.
if settings.mock_mode:
    repository = MockRepository()
    logger.info("Running with in-memory MockRepository (MOCK_MODE=true)")
else:
    repository = SqliteRepository()
    logger.info("Running with SQLite repository — data persists to pm_data.db")

# register all tool groups
register_project_tools(mcp, repository)
register_task_tools(mcp, repository)
register_team_tools(mcp, repository)
register_assignment_tools(mcp, repository)
register_planning_tools(mcp, repository)
register_analytics_tools(mcp, repository)
register_reporting_tools(mcp, repository)
register_insights_tools(mcp, repository)


if __name__ == "__main__":
    # stdio is the default transport for local MCP clients
    mcp.run(transport="stdio")
