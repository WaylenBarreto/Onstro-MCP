from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    @abstractmethod
    async def get_projects(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_project(self, project_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def update_project(self, project_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_project(self, project_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def list_tasks(self, project_id: int | None = None, **filters: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def update_task(self, task_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_task(self, task_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_team_members(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_team_member(self, member_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def assign_task(self, task_id: int, member_id: int) -> dict[str, Any] | None:
        raise NotImplementedError
