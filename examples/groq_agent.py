from __future__ import annotations

import os
import sys

os.environ["MOCK_MODE"] = "false"

from pm_mcp.tools.projects import ProjectTools


def ask_for_input(prompt_text: str) -> str:
    value = input(prompt_text).strip()
    if not value:
        raise ValueError(f"{prompt_text.strip()} cannot be empty.")
    return value


async def main() -> None:
    try:
        title = ask_for_input("Project title: ")
        description = ask_for_input("Project description: ")
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        raise SystemExit(1)

    tools = ProjectTools()
    result = await tools.create_project(
        name=title,
        description=description,
        priority="HIGH",
        owner_id=1,
    )

    if not result.get("success"):
        error = result.get("error", {})
        message = error.get("message") or error.get("code") or "Unknown live API error"
        print(f"Live project creation failed: {message}", file=sys.stderr)
        raise SystemExit(1)

    print("Project created successfully:")
    print(result["project"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
