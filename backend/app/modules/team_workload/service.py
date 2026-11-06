# OE-DELIVERY: 2026-10-23-team-workload-v1.2-filters (was 2026-10-23-team-workload-v1)
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Team Workload service — read-only track-record assembly.

Sources (no new tables, no writes):
  * ``oe_teams_membership`` joined via ``oe_teams_team`` — who is
    assigned to which project, in which role, since when.
  * ``oe_projects_project`` + ``oe_project_status_history`` — the bid
    flow: current status, and when the terminal status was reached.
  * ``oe_projects_award_pipeline`` (via the pipeline module's own
    ``build_view``) — the awarded flow: stage progress identical to
    the Awarded Projects pipeline tab, plus stage completion times.

Definitions used by the page:
  * A project is "awarded" when it has an award-pipeline row;
    otherwise it is a bid project.
  * A project is "completed" when its pipeline reached the
    ``completed`` stage, or (bid flow) its status is won / lost.
  * ``days`` runs from the assignment date (the person's own
    membership date in the individual view, the project's earliest
    assignment in the team view) to completion, or to now while the
    project is still running.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.award_pipeline import STAGE_LABELS, AwardPipeline
from app.modules.projects.models import Project, ProjectStatusHistory
from app.modules.projects.pipeline_service import build_view as build_pipeline_view
from app.modules.team_workload.schemas import (
    AssigneeOut,
    HistoryEventOut,
    TeamWorkloadOut,
    UserWorkloadDetailOut,
    WorkloadProjectOut,
    WorkloadUserOut,
)
from app.modules.teams.models import Team, TeamMembership
from app.modules.users.models import User

ROLE_LABELS: dict[str, str] = {
    "estimator": "Estimator",
    "project_manager": "Project Manager",
    "lead": "Lead",
    "owner": "Owner",
    "member": "Member",
    "viewer": "Viewer",
}

# Headline role when a person holds different roles on different
# projects: the most delivery-relevant one wins.
_ROLE_PRIORITY = ["estimator", "project_manager", "lead", "owner", "member", "viewer"]

# Bid-flow status -> (stage label, progress %). Awarded projects take
# their progress from the pipeline instead. Terminal bid statuses
# (won / lost) are handled as completed below.
_BID_STAGE: dict[str, tuple[str, int]] = {
    "new": ("New", 5),
    "estimation": ("Estimation", 30),
    "active": ("Estimation", 30),
    "estimation_submitted": ("Estimation Submitted", 50),
    "submitted_to_client": ("Submitted to Client", 65),
    "awaiting_response": ("Waiting Response", 80),
    "in_progress": ("In Progress", 40),
    "awarded": ("Awarded", 15),
    "on_hold": ("On Hold", 30),
    "won": ("Won", 100),
    "lost": ("Lost", 100),
}


def _aware(dt: datetime | None) -> datetime | None:
    """Normalise DB datetimes to aware UTC (some drivers return naive)."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _days_between(start: datetime | None, end: datetime | None) -> float | None:
    start = _aware(start)
    end = _aware(end)
    if start is None or end is None:
        return None
    return round(max((end - start).total_seconds(), 0.0) / 86400.0, 1)


def _role_label(role: str, custom_names: dict[str, str] | None = None) -> str:
    if custom_names and role in custom_names:
        return custom_names[role]
    return ROLE_LABELS.get(role, role.replace("_", " ").title())


def _headline_role(
    roles: list[str], custom_names: dict[str, str] | None = None
) -> str:
    for candidate in _ROLE_PRIORITY:
        if candidate in roles:
            return _role_label(candidate, custom_names)
    return _role_label(roles[0], custom_names) if roles else "Member"


async def _custom_role_names(
    session: AsyncSession, slugs: set[str]
) -> dict[str, str]:
    """Map custom_* membership slugs to their admin-defined names.

    OE-DELIVERY 2026-10-26 (role-first assign): membership roles can now
    be account roles, so a slug like ``custom_coordinator`` must display
    as "Coordinator", not the raw slug. Unknown or inactive slugs fall
    back to the title-cased slug in _role_label.
    """
    slugs = {s for s in slugs if isinstance(s, str) and s.startswith("custom_")}
    if not slugs:
        return {}
    try:
        from app.modules.users.models import CustomRole

        rows = (
            await session.execute(
                select(CustomRole).where(CustomRole.slug.in_(sorted(slugs)))
            )
        ).scalars().all()
        return {r.slug: r.name for r in rows}
    except Exception:  # noqa: BLE001 - labels only; never break the page
        return {}


class _ProjectFacts:
    """Per-project facts shared by the team and individual views."""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.assignees: list[AssigneeOut] = []
        self.kind = "bid"
        self.stage_label = ""
        self.progress = 0
        self.completed = False
        self.result: str | None = None
        self.completed_at: datetime | None = None
        self.pipeline_view = None

    def out(self, perspective_user_id: uuid.UUID | None) -> WorkloadProjectOut:
        p = self.project
        if perspective_user_id is not None:
            mine = next(
                (a for a in self.assignees if a.user_id == perspective_user_id),
                None,
            )
            assigned_at = mine.assigned_at if mine else None
        else:
            dated = [a.assigned_at for a in self.assignees if a.assigned_at]
            assigned_at = min(dated) if dated else _aware(p.created_at)
        end = _aware(self.completed_at) if self.completed else datetime.now(UTC)
        return WorkloadProjectOut(
            project_id=p.id,
            project_name=p.name,
            kind=self.kind,
            status=p.status,
            stage_label=self.stage_label,
            progress=self.progress,
            completed=self.completed,
            result=self.result,
            assigned_at=_aware(assigned_at),
            completed_at=_aware(self.completed_at),
            days=_days_between(assigned_at, end),
            assignees=self.assignees,
        )


async def _load_facts(session: AsyncSession) -> list[_ProjectFacts]:
    projects = (
        await session.execute(
            select(Project)
            .where(Project.status != "archived")
            .order_by(Project.created_at.desc())
        )
    ).scalars().all()
    by_id: dict[uuid.UUID, _ProjectFacts] = {p.id: _ProjectFacts(p) for p in projects}

    # ── Assignments: memberships on any of the project's teams,
    #    deduped per (project, user) keeping the earliest row. ────────
    rows = (
        await session.execute(
            select(TeamMembership, User, Team.project_id)
            .join(Team, Team.id == TeamMembership.team_id)
            .join(User, User.id == TeamMembership.user_id)
            .order_by(TeamMembership.created_at)
        )
    ).all()
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for membership, user, project_id in rows:
        facts = by_id.get(project_id)
        if facts is None:
            continue
        key = (project_id, user.id)
        if key in seen:
            continue
        seen.add(key)
        facts.assignees.append(
            AssigneeOut(
                user_id=user.id,
                full_name=user.full_name or "",
                email=user.email,
                role=membership.role,
                role_label=_role_label(membership.role),
                assigned_at=_aware(membership.created_at),
            )
        )

    # The project owner always counts as assigned (mirrors the
    # Team Strip rule in member_service.list_project_members).
    users_by_id: dict[uuid.UUID, User] = {u.id: u for _, u, _ in rows}
    for facts in by_id.values():
        p = facts.project
        if all(a.user_id != p.owner_id for a in facts.assignees):
            owner = users_by_id.get(p.owner_id)
            if owner is None:
                owner = (
                    await session.execute(select(User).where(User.id == p.owner_id))
                ).scalar_one_or_none()
                if owner is not None:
                    users_by_id[owner.id] = owner
            if owner is not None:
                facts.assignees.insert(
                    0,
                    AssigneeOut(
                        user_id=owner.id,
                        full_name=owner.full_name or "",
                        email=owner.email,
                        role="owner",
                        role_label="Owner",
                        assigned_at=_aware(p.created_at),
                    ),
                )

    # ── Awarded flow: pipeline progress identical to the pipeline tab.
    pipelines = (
        await session.execute(select(AwardPipeline))
    ).scalars().all()
    pipelines_by_project = {pl.project_id: pl for pl in pipelines}
    for project_id, pipeline in pipelines_by_project.items():
        facts = by_id.get(project_id)
        if facts is None:
            continue
        view = await build_pipeline_view(session, facts.project, pipeline)
        facts.kind = "awarded"
        facts.pipeline_view = view
        facts.progress = view.progress_pct
        if pipeline.current_stage == "completed":
            facts.completed = True
            facts.result = "Delivered"
            facts.stage_label = "Completed"
            done_times = [
                _aware(s.completed_at) for s in view.stages if s.completed_at
            ]
            facts.completed_at = max(done_times) if done_times else _aware(
                pipeline.delivered_at
            )
        else:
            facts.stage_label = STAGE_LABELS.get(
                pipeline.current_stage, pipeline.current_stage
            )

    # ── Bid flow: status ladder + terminal time from status history. ─
    history_rows = (
        await session.execute(
            select(ProjectStatusHistory).order_by(ProjectStatusHistory.created_at)
        )
    ).scalars().all()
    last_transition_to: dict[tuple[uuid.UUID, str], datetime] = {}
    for row in history_rows:
        last_transition_to[(row.project_id, row.to_status)] = row.created_at

    for facts in by_id.values():
        if facts.kind == "awarded":
            continue
        p = facts.project
        label, progress = _BID_STAGE.get(
            p.status, (p.status.replace("_", " ").title(), 0)
        )
        facts.stage_label = label
        facts.progress = progress
        if p.status in ("won", "lost"):
            facts.completed = True
            facts.result = "Won" if p.status == "won" else "Lost"
            facts.completed_at = _aware(
                last_transition_to.get((p.id, p.status)) or p.updated_at
            )

    # ── Custom role names (OE-DELIVERY 2026-10-26, role-first assign) ──
    # Membership roles can now be custom_* slugs; show the admin-defined
    # name on every assignee row instead of the raw slug.
    custom_slugs = {
        a.role for facts in by_id.values() for a in facts.assignees
        if a.role.startswith("custom_")
    }
    custom_names = await _custom_role_names(session, custom_slugs)
    if custom_names:
        for facts in by_id.values():
            for assignee in facts.assignees:
                if assignee.role in custom_names:
                    assignee.role_label = custom_names[assignee.role]

    return list(by_id.values())


def _user_out(
    user_id: uuid.UUID,
    name: str,
    email: str,
    roles: list[str],
    projects: list[WorkloadProjectOut],
    custom_names: dict[str, str] | None = None,
) -> WorkloadUserOut:
    completed_projects = [p for p in projects if p.completed]
    day_values = [p.days for p in completed_projects if p.days is not None]
    return WorkloadUserOut(
        user_id=user_id,
        full_name=name,
        email=email,
        role_label=_headline_role(roles, custom_names),
        total=len(projects),
        running=len(projects) - len(completed_projects),
        completed=len(completed_projects),
        won=sum(1 for p in completed_projects if p.result in ("Won", "Delivered")),
        avg_days=round(sum(day_values) / len(day_values), 1) if day_values else None,
    )


async def get_team_workload(session: AsyncSession, days: int = 0) -> TeamWorkloadOut:
    facts_list = await _load_facts(session)

    # Period filter (days > 0): completed projects finished before the
    # window drop out of BOTH the projects table and the per-person
    # stats, so the cards always describe the same set as the table.
    # Running projects are current workload — they always stay.
    if days > 0:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        facts_list = [
            f
            for f in facts_list
            if not f.completed
            or (f.completed_at is not None and _aware(f.completed_at) >= cutoff)
        ]

    projects_out = [f.out(None) for f in facts_list]

    per_user: dict[uuid.UUID, tuple[User, list[str], list[WorkloadProjectOut]]] = {}
    users = {
        u.id: u
        for u in (await session.execute(select(User))).scalars().all()
    }
    for facts in facts_list:
        for assignee in facts.assignees:
            user = users.get(assignee.user_id)
            if user is None:
                continue
            entry = per_user.setdefault(assignee.user_id, (user, [], []))
            entry[1].append(assignee.role)
            entry[2].append(facts.out(assignee.user_id))

    custom_names = await _custom_role_names(
        session,
        {a.role for f in facts_list for a in f.assignees},
    )
    users_out = [
        _user_out(uid, u.full_name or "", u.email, roles, projects, custom_names)
        for uid, (u, roles, projects) in per_user.items()
    ]
    users_out.sort(key=lambda x: (-x.running, -x.total, x.full_name.lower()))

    return TeamWorkloadOut(users=users_out, projects=projects_out)


async def get_user_workload(
    session: AsyncSession, user_id: uuid.UUID
) -> UserWorkloadDetailOut:
    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    facts_list = await _load_facts(session)
    mine = [
        f for f in facts_list if any(a.user_id == user_id for a in f.assignees)
    ]
    my_projects = [f.out(user_id) for f in mine]
    my_roles = [
        a.role for f in mine for a in f.assignees if a.user_id == user_id
    ]
    custom_names = await _custom_role_names(
        session,
        {a.role for f in mine for a in f.assignees} | {user.role},
    )
    user_out = _user_out(user_id, user.full_name or "", user.email, my_roles, my_projects, custom_names)
    if not my_roles:
        user_out.role_label = _role_label(user.role, custom_names)

    # ── History timeline ─────────────────────────────────────────────
    events: list[HistoryEventOut] = []
    project_names = {f.project.id: f.project.name for f in mine}

    for facts in mine:
        assignee = next(a for a in facts.assignees if a.user_id == user_id)
        if assignee.assigned_at is not None:
            events.append(
                HistoryEventOut(
                    date=assignee.assigned_at,
                    project_id=facts.project.id,
                    project_name=facts.project.name,
                    text=f"Assigned as {assignee.role_label}",
                )
            )

    my_project_ids = [f.project.id for f in mine]
    if my_project_ids:
        rows = (
            await session.execute(
                select(ProjectStatusHistory)
                .where(ProjectStatusHistory.project_id.in_(my_project_ids))
                .order_by(ProjectStatusHistory.created_at)
            )
        ).scalars().all()
        previous: dict[uuid.UUID, ProjectStatusHistory] = {}
        for row in rows:
            prev = previous.get(row.project_id)
            if row.from_status is None:
                text = f"Project created — status {_BID_STAGE.get(row.to_status, (row.to_status, 0))[0]}"
            else:
                from_label = _BID_STAGE.get(
                    row.from_status, (row.from_status.replace('_', ' ').title(), 0)
                )[0]
                to_label = _BID_STAGE.get(
                    row.to_status, (row.to_status.replace('_', ' ').title(), 0)
                )[0]
                text = f"Status: {from_label} → {to_label}"
                if prev is not None:
                    spent = _days_between(prev.created_at, row.created_at)
                    if spent is not None:
                        text += f" · {from_label} took {spent:g} days"
            if row.note:
                text += f" — {row.note}"
            events.append(
                HistoryEventOut(
                    date=_aware(row.created_at) or datetime.now(UTC),
                    project_id=row.project_id,
                    project_name=project_names.get(row.project_id, ""),
                    text=text,
                )
            )
            previous[row.project_id] = row

        for facts in mine:
            view = facts.pipeline_view
            if view is None:
                continue
            for stage in view.stages:
                if stage.state == "done" and stage.completed_at is not None:
                    events.append(
                        HistoryEventOut(
                            date=_aware(stage.completed_at) or datetime.now(UTC),
                            project_id=facts.project.id,
                            project_name=facts.project.name,
                            text=f"Stage complete: {stage.label}",
                        )
                    )

    events.sort(key=lambda e: e.date, reverse=True)
    return UserWorkloadDetailOut(
        user=user_out, projects=my_projects, history=events[:20]
    )
