from __future__ import annotations

import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    env = os.environ.copy()
    env.setdefault("MOCK_MODE", "true")
    params = StdioServerParameters(
        command="python",
        args=["-m", "pm_mcp.server"],
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools.tools])

            project_result = await session.call_tool(
                "create_project",
                {
                    "name": "Restaurant Delivery Website",
                    "description": "Create landing, ordering and checkout flows.",
                    "priority": "HIGH",
                    "owner_id": 1,
                },
            )
            print(project_result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
