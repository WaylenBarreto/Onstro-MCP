from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import Any

from pm_mcp.repositories.base import BaseRepository


class MockRepository(BaseRepository):
    def __init__(self) -> None:
        self.projects: list[dict[str, Any]] = []
        self.tasks: list[dict[str, Any]] = []
        self.members: list[dict[str, Any]] = [
            {"id": 1, "name": "Alice", "email": "alice@company.com", "role": "Project Manager", "skills": ["planning", "risk", "communication"], "availability": 0.8, "max_weekly_hours": 40, "current_workload": 26},
            {"id": 2, "name": "Bob", "email": "bob@company.com", "role": "Backend Developer", "skills": ["python", "api", "database", "security"], "availability": 0.9, "max_weekly_hours": 40, "current_workload": 28},
            {"id": 3, "name": "Carla", "email": "carla@company.com", "role": "Frontend Developer", "skills": ["react", "ux", "javascript", "html"], "availability": 0.7, "max_weekly_hours": 32, "current_workload": 22},
            {"id": 4, "name": "David", "email": "david@company.com", "role": "QA Engineer", "skills": ["testing", "automation", "security"], "availability": 0.85, "max_weekly_hours": 38, "current_workload": 18},
            {"id": 5, "name": "Sarah", "email": "sarah@company.com", "role": "Full Stack Developer", "skills": ["python", "react", "api", "ux"], "availability": 0.95, "max_weekly_hours": 40, "current_workload": 12},
        ]
        self._seed()

    def _seed(self) -> None:
        now = datetime.now()
        project = {
            "id": 1,
            "name": "Restaurant Food Delivery Website",
            "description": "Launch a restaurant and food delivery web experience in 14 days.",
            "status": "ACTIVE",
            "priority": "HIGH",
            "owner_id": 1,
            "start_date": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
            "due_date": (now + timedelta(days=12)).strftime("%Y-%m-%d"),
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": now.isoformat(),
        }
        self.projects.append(project)
        self.tasks.extend([
            {"id": 1, "project_id": 1, "title": "Requirements and scope", "description": "Finalize scope and acceptance criteria.", "status": "DONE", "priority": "HIGH", "assignee_id": 1, "estimated_hours": 8, "due_date": (now - timedelta(days=1)).strftime("%Y-%m-%d"), "parent_task_id": None, "dependencies": [], "created_at": (now - timedelta(days=5)).isoformat(), "updated_at": (now - timedelta(days=2)).isoformat()},
            {"id": 2, "project_id": 1, "title": "Authentication and user accounts", "description": "Build login/signup and profile management.", "status": "IN_PROGRESS", "priority": "HIGH", "assignee_id": 2, "estimated_hours": 20, "due_date": (now + timedelta(days=4)).strftime("%Y-%m-%d"), "parent_task_id": None, "dependencies": [], "created_at": (now - timedelta(days=3)).isoformat(), "updated_at": now.isoformat()},
            {"id": 3, "project_id": 1, "title": "Payment integration", "description": "Integrate payment gateway for checkout.", "status": "TODO", "priority": "HIGH", "assignee_id": 5, "estimated_hours": 16, "due_date": (now + timedelta(days=6)).strftime("%Y-%m-%d"), "parent_task_id": None, "dependencies": [2], "created_at": (now - timedelta(days=2)).isoformat(), "updated_at": now.isoformat()},
            {"id": 4, "project_id": 1, "title": "Restaurant listing and search", "description": "Create restaurant catalog and search.", "status": "TODO", "priority": "MEDIUM", "assignee_id": 3, "estimated_hours": 18, "due_date": (now + timedelta(days=7)).strftime("%Y-%m-%d"), "parent_task_id": None, "dependencies": [], "created_at": (now - timedelta(days=2)).isoformat(), "updated_at": now.isoformat()},
            {"id": 5, "project_id": 1, "title": "QA testing and regression", "description": "Validate the full workflow.", "status": "TODO", "priority": "HIGH", "assignee_id": 4, "estimated_hours": 12, "due_date": (now + timedelta(days=8)).strftime("%Y-%m-%d"), "parent_task_id": None, "dependencies": [2, 3], "created_at": (now - timedelta(days=1)).isoformat(), "updated_at": now.isoformat()},
        ])

    async def get_projects(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.projects)

    async def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        new_id = max((p["id"] for p in self.projects), default=0) + 1
        created = {**payload, "id": new_id, "status": payload.get("status", "PLANNING"), "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}
        self.projects.append(created)
        return copy.deepcopy(created)

    async def get_project(self, project_id: int) -> dict[str, Any] | None:
        for project in self.projects:
            if project["id"] == project_id:
                return copy.deepcopy(project)
        return None

    async def update_project(self, project_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        for idx, project in enumerate(self.projects):
            if project["id"] == project_id:
                updated = {**project, **fields, "updated_at": datetime.now().isoformat()}
                self.projects[idx] = updated
                return copy.deepcopy(updated)
        return None

    async def delete_project(self, project_id: int) -> bool:
        before = len(self.projects)
        self.projects = [project for project in self.projects if project["id"] != project_id]
        self.tasks = [task for task in self.tasks if task["project_id"] != project_id]
        return len(self.projects) < before

    async def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        new_id = max((task["id"] for task in self.tasks), default=0) + 1
        created = {**payload, "id": new_id, "status": payload.get("status", "TODO"), "dependencies": payload.get("dependencies", []), "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}
        self.tasks.append(created)
        return copy.deepcopy(created)

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        for task in self.tasks:
            if task["id"] == task_id:
                return copy.deepcopy(task)
        return None

    async def list_tasks(self, project_id: int | None = None, **filters: Any) -> list[dict[str, Any]]:
        tasks = [task for task in self.tasks if project_id is None or task["project_id"] == project_id]
        for key, value in filters.items():
            if value is None:
                continue
            if key == "status":
                tasks = [task for task in tasks if task.get("status") == value]
            elif key == "priority":
                tasks = [task for task in tasks if task.get("priority") == value]
            elif key == "assignee_id":
                tasks = [task for task in tasks if task.get("assignee_id") == value]
        return copy.deepcopy(tasks)

    async def update_task(self, task_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        for idx, task in enumerate(self.tasks):
            if task["id"] == task_id:
                updated = {**task, **fields, "updated_at": datetime.now().isoformat()}
                self.tasks[idx] = updated
                return copy.deepcopy(updated)
        return None

    async def delete_task(self, task_id: int) -> bool:
        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if task["id"] != task_id]
        return len(self.tasks) < before

    async def list_team_members(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.members)

    async def get_team_member(self, member_id: int) -> dict[str, Any] | None:
        for member in self.members:
            if member["id"] == member_id:
                return copy.deepcopy(member)
        return None

    async def assign_task(self, task_id: int, member_id: int) -> dict[str, Any] | None:
        for idx, task in enumerate(self.tasks):
            if task["id"] == task_id:
                self.tasks[idx]["assignee_id"] = member_id
                self.tasks[idx]["updated_at"] = datetime.now().isoformat()
                return copy.deepcopy(self.tasks[idx])
        return None
