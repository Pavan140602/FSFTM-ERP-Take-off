# OE-DELIVERY: 2026-10-23-team-workload-v1.2-filters (was 2026-10-23-team-workload-v1)
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Team Workload API routes.

Mounted by the module loader at ``/api/v1/team-workload`` (the
``/api/v1/team_workload`` form is mirrored automatically).

Endpoints:
    GET    /                 - Team view: per-person summary + all projects.
                               ``?days=N`` keeps only projects completed in
                               the last N days (running always stay); the
                               per-person stats follow the same window.
    GET    /users/{user_id}/ - Individual view: one person's projects + history
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.dependencies import RequirePermission, SessionDep
from app.modules.team_workload import service
from app.modules.team_workload.schemas import TeamWorkloadOut, UserWorkloadDetailOut

router = APIRouter(tags=["team-workload"])


@router.get(
    "/",
    response_model=TeamWorkloadOut,
    dependencies=[Depends(RequirePermission("team_workload.read"))],
)
async def team_workload(
    session: SessionDep, days: int = Query(default=0, ge=0)
) -> TeamWorkloadOut:
    return await service.get_team_workload(session, days=days)


@router.get(
    "/users/{user_id}/",
    response_model=UserWorkloadDetailOut,
    dependencies=[Depends(RequirePermission("team_workload.read"))],
)
async def user_workload(session: SessionDep, user_id: uuid.UUID) -> UserWorkloadDetailOut:
    return await service.get_user_workload(session, user_id)
