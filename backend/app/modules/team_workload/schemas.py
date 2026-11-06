# OE-DELIVERY: 2026-10-23-team-workload-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Team Workload API schemas.

Everything here is a read model assembled from existing tables:
``oe_teams_membership`` (assignments), ``oe_projects_project`` +
``oe_project_status_history`` (bid flow + stage durations) and
``oe_projects_award_pipeline`` (awarded flow). ``days`` is always
measured from the person's assignment date (or, in the team view,
the project's earliest assignment) to completion - or to now while
the project is still running.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AssigneeOut(BaseModel):
    user_id: UUID
    full_name: str = ""
    email: str = ""
    role: str = "member"
    role_label: str = "Member"
    assigned_at: datetime | None = None


class WorkloadProjectOut(BaseModel):
    project_id: UUID
    project_name: str
    kind: str  # 'bid' | 'awarded'
    status: str
    stage_label: str
    progress: int = 0  # 0..100
    completed: bool = False
    result: str | None = None  # 'Won' | 'Lost' | 'Delivered'
    assigned_at: datetime | None = None
    completed_at: datetime | None = None
    days: float | None = None
    assignees: list[AssigneeOut] = Field(default_factory=list)


class WorkloadUserOut(BaseModel):
    user_id: UUID
    full_name: str = ""
    email: str = ""
    role_label: str = "Member"
    total: int = 0
    running: int = 0
    completed: int = 0
    won: int = 0
    avg_days: float | None = None


class TeamWorkloadOut(BaseModel):
    users: list[WorkloadUserOut] = Field(default_factory=list)
    projects: list[WorkloadProjectOut] = Field(default_factory=list)


class HistoryEventOut(BaseModel):
    date: datetime
    project_id: UUID
    project_name: str = ""
    text: str = ""


class UserWorkloadDetailOut(BaseModel):
    user: WorkloadUserOut
    projects: list[WorkloadProjectOut] = Field(default_factory=list)
    history: list[HistoryEventOut] = Field(default_factory=list)
