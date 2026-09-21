from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from pm_mcp.config import get_app_settings

logger = logging.getLogger(__name__)


class PMApiClientError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class PMApiClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, tenant_id: str | None = None, app_id: str | None = None, timeout: int = 30, retries: int = 3):
        settings = get_app_settings()
        self.base_url = (base_url or settings.pm_api_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.pm_api_key
        self.tenant_id = tenant_id if tenant_id is not None else settings.pm_tenant_id
        self.app_id = app_id if app_id is not None else settings.pm_app_id
        self.timeout = timeout or settings.pm_api_timeout
        self.retries = retries or settings.pm_api_retries
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.tenant_id:
            headers["X-TenantId"] = self.tenant_id
        if self.app_id:
            headers["X-AppId"] = self.app_id


        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                logger.info("PM API request", extra={"method": method, "url": url, "attempt": attempt})
                response = await self._client.request(method, url, headers=headers, json=json_body, params=params)
                logger.info(
                    "PM API response",
                    extra={"method": method, "url": url, "status": response.status_code, "attempt": attempt},
                )
                if response.status_code >= 500:
                    raise PMApiClientError("PM_API_UNAVAILABLE", "The project management API is currently unavailable.", response.status_code)
                if response.status_code in (400, 401, 403, 404, 409):
                    try:
                        payload = response.json()
                        msg = payload.get("message") or payload.get("error") or response.text
                    except Exception:
                        msg = response.text
                    raise PMApiClientError("PM_API_ERROR", msg, response.status_code)
                if response.status_code == 204:
                    return None
                try:
                    data = response.json()
                except ValueError as exc:
                    raise PMApiClientError("PM_API_INVALID_RESPONSE", "The project management API returned an invalid JSON response.", response.status_code) from exc
                if response.status_code >= 300:
                    raise PMApiClientError("PM_API_ERROR", "Unexpected API error.", response.status_code)
                return data
            except (httpx.TimeoutException, httpx.NetworkError, PMApiClientError) as exc:
                last_exc = exc
                if attempt >= self.retries:
                    if isinstance(exc, PMApiClientError):
                        raise
                    raise PMApiClientError("PM_API_UNAVAILABLE", "The project management API is currently unavailable.") from exc
                await asyncio.sleep(0.2 * attempt)

        if last_exc is not None:
            if isinstance(last_exc, PMApiClientError):
                raise last_exc
            raise PMApiClientError("PM_API_UNAVAILABLE", "The project management API is currently unavailable.") from last_exc
        raise PMApiClientError("PM_API_UNAVAILABLE", "The project management API is currently unavailable.")

    async def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/projects", json_body=payload)

    async def get_project(self, project_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/projects/{project_id}")

    async def list_projects(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return await self._request("GET", "/projects", params=filters or {})

    async def update_project(self, project_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PATCH", f"/projects/{project_id}", json_body=fields)

    async def delete_project(self, project_id: int) -> dict[str, Any]:
        return await self._request("DELETE", f"/projects/{project_id}")

    async def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/tasks", json_body=payload)

    async def get_task(self, task_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/tasks/{task_id}")

    async def list_tasks(self, project_id: int | None = None, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params = dict(filters or {})
        if project_id is not None:
            params["projectId"] = project_id
        return await self._request("GET", "/tasks", params=params)

    async def update_task(self, task_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PATCH", f"/tasks/{task_id}", json_body=fields)

    async def delete_task(self, task_id: int) -> dict[str, Any]:
        return await self._request("DELETE", f"/tasks/{task_id}")

    async def complete_task(self, task_id: int) -> dict[str, Any]:
        return await self._request("POST", f"/tasks/{task_id}/complete")

    async def list_team_members(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/team/members")

    async def get_team_member(self, member_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/team/members/{member_id}")

    async def get_member_workload(self, member_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/team/members/{member_id}/workload")

    async def get_team_workload(self) -> dict[str, Any]:
        return await self._request("GET", "/team/workload")

    async def assign_task(self, task_id: int, member_id: int) -> dict[str, Any]:
        return await self._request("POST", f"/tasks/{task_id}/assign", json_body={"memberId": member_id})
