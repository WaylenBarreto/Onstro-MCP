from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

from pm_mcp.config import get_app_settings
from pm_mcp.logging_config import configure_logging
from pm_mcp.repositories.mock_repository import MockRepository
from pm_mcp.tools.projects import register_project_tools
from pm_mcp.tools.tasks import register_task_tools
from pm_mcp.tools.team import register_team_tools
from pm_mcp.tools.assignment import register_assignment_tools
from pm_mcp.tools.planning import register_planning_tools
from pm_mcp.tools.analytics import register_analytics_tools
from pm_mcp.tools.reporting import register_reporting_tools

configure_logging(get_app_settings().log_level)
logger = logging.getLogger(__name__)

mcp = MCPServer("pm-project-manager")
repository = MockRepository() if get_app_settings().mock_mode else None


# register all tool groups
register_project_tools(mcp, repository)
register_task_tools(mcp, repository)
register_team_tools(mcp, repository)
register_assignment_tools(mcp, repository)
register_planning_tools(mcp, repository)
register_analytics_tools(mcp, repository)
register_reporting_tools(mcp, repository)


if __name__ == "__main__":
    # stdio is the default transport for local MCP clients
    mcp.run(transport="stdio")
