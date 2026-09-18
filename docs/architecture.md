# Architecture

## Overview

This project implements a Python-based MCP server that sits between an AI agent and a C# ASP.NET Core project-management platform.

The architecture enforces separation of concerns:

- MCP layer: exposes tool definitions for agent use
- API client: calls the C# API through HTTP/REST
- Repository layer: provides mock and production behavior
- Business engines: assignment, dependency, workload, risk, schedule, and duplicate analysis
- Models: typed Pydantic data structures
- Configuration: environment-based settings

## Runtime flow

1. The user interacts with a Groq-based AI agent.
2. The agent selects one or more MCP tools.
3. The MCP server validates input and calls the appropriate repository or API client.
4. Data is returned in structured JSON.
5. The agent explains the result to the user.

## Mock mode

MOCK_MODE=true routes requests to the in-memory repository rather than the C# API. This allows local validation, demo flows, and CI tests without a backend dependency.

## Production mode

When MOCK_MODE=false, the server talks only to PM_API_BASE_URL and uses PM_API_KEY if configured. It does not connect to a database or other internal resources.

## Safety boundaries

- No direct database access
- No arbitrary outbound URL calls
- No secret leakage in logs
- Destructive operations clearly flagged in descriptions
- Dry-run support for bulk assignment and workload balancing
