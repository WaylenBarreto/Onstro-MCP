from __future__ import annotations

from pydantic import BaseModel, Field


class MemberSkillModel(BaseModel):
    member_id: int
    skills: list[str] = Field(default_factory=list)


class WorkloadSummary(BaseModel):
    member_id: int
    name: str
    role: str | None = None
    assigned_hours: float = 0.0
    maximum_hours: float = 0.0
    utilization_percentage: float = 0.0
    active_task_count: int = 0
    overdue_task_count: int = 0


class TeamWorkloadReport(BaseModel):
    members: list[WorkloadSummary] = Field(default_factory=list)
    overloaded_members: list[int] = Field(default_factory=list)
    underutilized_members: list[int] = Field(default_factory=list)
    imbalance_score: float = 0.0
