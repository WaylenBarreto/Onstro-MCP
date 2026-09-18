from __future__ import annotations

from pydantic import BaseModel, Field


class RiskItem(BaseModel):
    type: str
    severity: str
    description: str
    affected_tasks: list[int] = Field(default_factory=list)
    recommended_action: str


class ProjectHealthReport(BaseModel):
    project_id: int
    completion_percentage: float
    schedule_status: str
    workload_status: str
    dependency_status: str
    risk_count: int
    blocker_count: int
    recommendations: list[str] = Field(default_factory=list)


class AssignmentRecommendation(BaseModel):
    recommended_member: dict | None = None
    score: float = 0.0
    alternative_candidates: list[dict] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    workload_impact: dict = Field(default_factory=dict)
    potential_risks: list[str] = Field(default_factory=list)
