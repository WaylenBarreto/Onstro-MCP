from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProjectModel(BaseModel):
    id: int | None = None
    name: str
    description: str | None = None
    status: Literal["PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"] = "PLANNING"
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    owner_id: int | None = None
    start_date: str | None = None
    due_date: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"extra": "allow"}


class TaskModel(BaseModel):
    id: int | None = None
    project_id: int
    title: str
    description: str | None = None
    status: Literal["TODO", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE", "CANCELLED"] = "TODO"
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    assignee_id: int | None = None
    estimated_hours: float | None = None
    due_date: str | None = None
    parent_task_id: int | None = None
    dependencies: list[int] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"extra": "allow"}


class TeamMemberModel(BaseModel):
    id: int
    name: str
    email: str | None = None
    role: str | None = None
    skills: list[str] = Field(default_factory=list)
    availability: float = 1.0
    max_weekly_hours: float = 40.0
    current_workload: float = 0.0

    model_config = {"extra": "allow"}


class MilestoneModel(BaseModel):
    id: int | None = None
    project_id: int
    name: str
    description: str | None = None
    due_date: str | None = None
    status: Literal["PLANNED", "ACTIVE", "COMPLETED"] = "PLANNED"


class DependencyModel(BaseModel):
    task_id: int
    depends_on_task_id: int
    dependency_type: str = "BLOCKS"


class ProjectPlan(BaseModel):
    project: dict[str, Any] = Field(default_factory=dict)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    success: bool = False
    error: dict[str, str]
