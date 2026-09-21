"""
Groq AI Agent for Onstro MCP
==============================
Architecture:
    User prompt
        → Groq LLM (llama-3.3-70b-versatile) with MCP tool definitions
        → LLM selects tool(s)
        → MCP server executes tool via stdio transport
        → Result fed back to LLM
        → Final natural-language answer returned to user

Usage:
    # Interactive mode
    py examples/groq_agent.py

    # One-shot mode
    py examples/groq_agent.py "List all projects and show me the risks for project 1"
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

# ── resolve project root so we can find the .env ──────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

# Let MOCK_MODE be read from .env (MOCK_MODE=FALSE → SqliteRepository with real persistence)

from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from pm_mcp.config import get_settings

# Best available tool-calling model on this Groq account
GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are an AI project management assistant for the Onstro platform.
You have access to tools that let you manage projects, tasks, team members, assignments, analytics, and insights.

Guidelines:
- Always use the available tools to fetch real data before answering.
- When creating or modifying data, confirm what you did.
- Format responses in a clear, readable way.
- If a user asks about risks, workload, or schedule — use the analytics tools.
- For assignment questions, use recommend_assignee or auto_assign_project.
"""


def _mcp_tool_to_groq(tool: Any) -> dict[str, Any]:
    """Convert an MCP ToolDef to Groq's function-calling schema."""
    schema = tool.input_schema or {"type": "object", "properties": {}}
    # Groq requires the schema to have a "type" key
    if "type" not in schema:
        schema = {"type": "object", "properties": schema}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": (tool.description or "").strip(),
            "parameters": schema,
        },
    }


async def run_agent(user_message: str, *, verbose: bool = True) -> str:
    """
    Run a full agentic conversation turn.

    Returns the assistant's final text response.
    """
    settings = get_settings()
    api_key = settings.groq_api_key_value or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to your .env file:\n"
            "  GROQ_API_KEY=gsk_..."
        )

    groq_client = Groq(api_key=api_key)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "pm_mcp.server"],
        env=os.environ.copy(),   # inherits MOCK_MODE from .env
        cwd=_ROOT,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # ── Fetch all MCP tools ────────────────────────────────────────────
            tools_result = await session.list_tools()
            groq_tools = [_mcp_tool_to_groq(t) for t in tools_result.tools]

            if verbose:
                print(f"[tools]  {len(groq_tools)} MCP tools loaded")
                print(f"[user ]  {user_message}\n")

            messages: list[dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]

            # ── Agentic loop ───────────────────────────────────────────────────
            iteration = 0
            max_iterations = 10   # safety cap
            _EMPTY_ERR = "model output must contain either output text or tool calls"

            def _call_groq(msgs: list, temp: float = 0.2):
                """Call Groq and retry up to 3x on empty-response errors."""
                for attempt in range(3):
                    try:
                        resp = groq_client.chat.completions.create(
                            model=GROQ_MODEL,
                            messages=msgs,
                            tools=groq_tools,
                            tool_choice="auto",
                            max_tokens=4096,
                            temperature=temp + attempt * 0.1,
                        )
                        _m = resp.choices[0].message
                        # If content and tool_calls are both empty, treat as failure
                        if not _m.tool_calls and not (_m.content or "").strip():
                            if attempt < 2:
                                # Nudge and retry
                                msgs = msgs + [{"role": "user", "content": "Please respond or call an appropriate tool."}]
                                continue
                        return resp
                    except Exception as exc:
                        if _EMPTY_ERR in str(exc) and attempt < 2:
                            continue
                        raise
                return None

            while iteration < max_iterations:
                iteration += 1

                response = _call_groq(messages)
                if response is None:
                    return "[agent]  Model returned no response after retries. Please try again."

                choice = response.choices[0]
                msg = choice.message

                # Final guard: still empty after retries
                if not msg.tool_calls and not (msg.content or "").strip():
                    return "[agent]  Model returned an empty response. Please rephrase your request."

                if msg.tool_calls:
                    # ── Append assistant turn with tool_calls ──────────────────
                    messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    })

                    # ── Execute each tool call via the MCP server ──────────────
                    for tc in msg.tool_calls:
                        fn_name = tc.function.name
                        try:
                            fn_args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            fn_args = {}

                        if verbose:
                            args_preview = json.dumps(fn_args, ensure_ascii=False)
                            print(f"[call]   {fn_name}({args_preview})")

                        mcp_result = await session.call_tool(fn_name, fn_args)

                        # MCP returns a list of content items; grab the first text
                        if mcp_result.content:
                            result_text = mcp_result.content[0].text
                        else:
                            result_text = json.dumps({"success": True})

                        if verbose:
                            preview = result_text[:300]
                            suffix = "..." if len(result_text) > 300 else ""
                            print(f"   -> Result: {preview}{suffix}\n")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result_text,
                        })

                else:
                    # ── No more tool calls -> final answer ────────────────────
                    final_answer = msg.content or ""
                    if verbose:
                        print(f"[agent]  Assistant:\n{final_answer}")
                    return final_answer

            return "[agent]  Reached max iterations without a final answer."


def main() -> None:
    # Reconfigure stdout/stderr to UTF-8 so output works on Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    if not query:
        try:
            query = input("What would you like to do? ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return

    if not query:
        print("No input provided.", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(run_agent(query))
    except RuntimeError as exc:
        print(f"[error]  {exc}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
