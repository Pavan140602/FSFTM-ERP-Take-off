# OE-DELIVERY: 2026-10-27-receipt-edit (was 2026-10-27-payment-receipts)
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""Post-Award Pipeline — business logic.

Stage flow (see award_pipeline.py for the design):

    work stages (drafting -> shop_drawings -> seal_sign -> fabrication ->
    delivery -> feedback -> completed) with payment milestones woven
    between them by anchor. The default schedule is 10% on award ->
    60% after Seal & Sign -> 30% after Fabrication, but each project may
    carry 3-5 milestones with custom percents and anchors - always
    collected in full BEFORE delivery.

Entering a payment milestone emails the Accounts team the project
details. Marking the milestone "Received" releases the next stage. No
Finance invoice is ever created - Accounts invoices externally.

Partial receipts (OE-DELIVERY 2026-10-27): money arrives in
unpredictable amounts, so any number of receipts can be recorded
against a milestone at whatever percent actually arrived. Received is
the sum of receipts, balance is target minus received. Reaching the
target completes the milestone exactly as "Mark Payment Received"
does, and sends one automatic completion email (the only automatic
email in the feature - gate invoice emails stay manual). Overpayment
carries forward to the next milestone in schedule order; past the
final milestone it stays flagged as excess, never silently dropped.
"""

from __future__ import annotations

import html
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.award_pipeline import (
    DEFAULT_MILESTONES,
    LEGACY_ANCHOR_COLUMNS,
    MAX_MILESTONES,
    MILESTONE_ANCHORS,
    MIN_MILESTONES,
    STAGE_LABELS,
    WORK_STAGE_ORDER,
    AccountsUserOut,
    AwardPipeline,
    DeliveryIn,
    FabricationIn,
    FeedbackSendIn,
    InvoiceEmailIn,
    PipelineActivity,
    PipelineActivityOut,
    PipelineMilestone,
    PipelineMilestoneOut,
    PipelineReceipt,
    PipelineReceiptIn,
    PipelineReceiptOut,
    PipelineReceiptUpdate,
    PipelineRevision,
    PipelineRevisionOut,
    PipelineSend,
    PipelineSendIn,
    PipelineSendOut,
    PipelineStageOut,
    PipelineView,
    RejectSealIn,
    RevisionIn,
    SaveScheduleIn,
    ShopSentIn,
)
from app.modules.projects.models import Project

logger = logging.getLogger(__name__)

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_money(raw: str | None) -> float | None:
    """Contract values are stored as strings ('485000', '$485,000')."""
    if not raw:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(raw))
    if not cleaned or cleaned in ("-", ".", "-."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _gate_amount(project: Project, pct: int) -> float | None:
    value = _parse_money(project.contract_value)
    if value is None:
        return None
    return round(value * pct / 100.0, 2)


async def _get_project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    project = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


async def _client_name(session: AsyncSession, project: Project) -> str | None:
    if not project.client_id:
        return None
    try:
        from app.modules.crm.models import Account

        account = (
            await session.execute(
                select(Account).where(Account.id == uuid.UUID(str(project.client_id)))
            )
        ).scalar_one_or_none()
        if account is not None:
            return account.name
    except Exception:  # noqa: BLE001 - client name is display-only
        logger.debug("pipeline: client lookup failed", exc_info=True)
    return None


async def _log(
    session: AsyncSession,
    pipeline: AwardPipeline,
    text: str,
    actor_id: uuid.UUID | None,
) -> None:
    session.add(
        PipelineActivity(
            pipeline_id=pipeline.id,
            project_id=pipeline.project_id,
            text=text,
            actor_id=actor_id,
        )
    )


# ── Accounts email ────────────────────────────────────────────────────


# ── Schema self-heal ─────────────────────────────────────────────────
# This product never runs `alembic upgrade`, and create_all never
# alters existing tables — so a column added to the model can be
# missing on an installed database, and every pipeline query then
# fails (UndefinedColumnError). Heal both pipeline tables from the
# model metadata, once per process. Types are compiled from the
# models themselves, so they always match what create_all emits
# (GUID -> VARCHAR(36) etc.). This replaces the one-off ALTER scripts.
# OE-DELIVERY 2026-10-22 v10: this declaration was accidentally removed
# with the dead auto-mailer in v9 (NameError on every pipeline call) —
# restored verbatim.
_schema_healed = False


async def _ensure_pipeline_schema(session: AsyncSession) -> None:
    global _schema_healed
    if _schema_healed:
        return
    try:
        from sqlalchemy import text as _sa_text
        from sqlalchemy.dialects import postgresql as _pg_mod

        dialect = _pg_mod.dialect()
        for model in (AwardPipeline, PipelineSend, PipelineMilestone, PipelineReceipt):
            table = model.__table__
            rows = (
                await session.execute(
                    _sa_text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :t"
                    ),
                    {"t": table.name},
                )
            ).fetchall()
            existing = {r[0] for r in rows}
            for col in table.columns:
                if col.name in existing:
                    continue
                ddl_type = col.type.compile(dialect=dialect)
                stmt = (
                    f"ALTER TABLE {table.name} "
                    f'ADD COLUMN IF NOT EXISTS "{col.name}" {ddl_type}'
                )
                default = col.default
                if (
                    not col.nullable
                    and default is not None
                    and getattr(default, "arg", None) is not None
                    and not callable(default.arg)
                ):
                    arg = default.arg
                    if isinstance(arg, bool):
                        stmt += f" DEFAULT {'true' if arg else 'false'}"
                    elif isinstance(arg, (int, float)):
                        stmt += f" DEFAULT {arg}"
                    else:
                        stmt += f" DEFAULT '{arg}'"
                    stmt += " NOT NULL"
                await session.execute(_sa_text(stmt))
                logger.warning(
                    "pipeline schema heal: added %s.%s (%s)",
                    table.name,
                    col.name,
                    ddl_type,
                )
        await session.commit()
        _schema_healed = True
    except Exception:  # noqa: BLE001 - best-effort; real errors surface in the query
        logger.warning("pipeline schema heal failed", exc_info=True)
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass


# -- Flexible payment schedule (OE-DELIVERY 2026-10-27) --
# The dynamic stage order weaves payment milestones between the fixed
# work stages. A milestone's stage key is "payment_<key>" (short, so it
# fits the pipeline's String(30) current_stage column).


def _milestone_stage_key(m: PipelineMilestone) -> str:
    return f"payment_{m.key}"


def _dynamic_order(milestones: list[PipelineMilestone]) -> list[str]:
    """Stage keys in display order: award milestone first, then each
    work stage followed by the milestones anchored after it (by seq).
    before_delivery rows follow fabrication, before delivery."""
    by_work: dict[str, list[PipelineMilestone]] = {}
    award: PipelineMilestone | None = None
    for m in milestones:
        if m.anchor == "award":
            award = m
        else:
            by_work.setdefault(MILESTONE_ANCHORS[m.anchor][1], []).append(m)
    for rows in by_work.values():
        rows.sort(key=lambda r: r.seq)
    order: list[str] = []
    if award is not None:
        order.append(_milestone_stage_key(award))
    for work in WORK_STAGE_ORDER:
        order.append(work)
        for m in by_work.get(work, []):
            order.append(_milestone_stage_key(m))
    return order


async def _load_milestones(
    session: AsyncSession, pipeline_id: uuid.UUID
) -> list[PipelineMilestone]:
    rows = (
        await session.execute(
            select(PipelineMilestone)
            .where(PipelineMilestone.pipeline_id == pipeline_id)
            .order_by(PipelineMilestone.seq.asc())
        )
    ).scalars().all()
    return list(rows)


# -- Partial receipts (OE-DELIVERY 2026-10-27) --
# A milestone's received percent is the sum of its NON-excess
# receipts; balance is target minus received; excess is the overshoot
# kept on the final milestone. All amounts round to 2 decimals so
# float sums never show as 29.999999 or complete a target early.


def _receipt_sums(
    receipts: list[PipelineReceipt],
) -> tuple[float, float]:
    """(received, excess) for one milestone's receipt rows."""
    received = round(
        sum(r.percent for r in receipts if not r.is_excess), 2
    )
    excess = round(sum(r.percent for r in receipts if r.is_excess), 2)
    return received, excess


async def _load_receipts(
    session: AsyncSession, pipeline_id: uuid.UUID
) -> dict[uuid.UUID, list[PipelineReceipt]]:
    """Receipt rows grouped by milestone id, in recorded order."""
    milestones = await _load_milestones(session, pipeline_id)
    ids = [m.id for m in milestones]
    grouped: dict[uuid.UUID, list[PipelineReceipt]] = {i: [] for i in ids}
    if not ids:
        return grouped
    rows = (
        await session.execute(
            select(PipelineReceipt)
            .where(PipelineReceipt.milestone_id.in_(ids))
            .order_by(
                PipelineReceipt.milestone_id.asc(),
                PipelineReceipt.seq.asc(),
                PipelineReceipt.created_at.asc(),
            )
        )
    ).scalars().all()
    for row in rows:
        grouped.setdefault(row.milestone_id, []).append(row)
    return grouped


def _plan_receipts(
    state: list[dict],
    target_index: int,
    incoming: float,
) -> tuple[list[tuple[int, float, bool]], list[int]]:
    """Pure allocation plan for one recorded receipt.

    ``state`` is the schedule's payment milestones in schedule order,
    each ``{"target": float, "received": float, "complete": bool}``.
    ``target_index`` is where the receipt was recorded, ``incoming``
    the percent entered. Returns (allocations, completed_indices):
    allocations are (milestone index, percent, is_excess) rows in
    order; completed indices are milestones that reach their target
    through this receipt. Walk-forward rule: fill the target, then
    carry any remainder to the next INCOMPLETE milestone; leftover
    past the last milestone lands as an excess row on the final
    milestone, never dropped. Already-complete milestones are skipped
    in the walk. Pure stdlib - unit-testable without the app.
    """
    allocations: list[tuple[int, float, bool]] = []
    completed: list[int] = []
    remaining = round(incoming, 2)
    i = target_index
    while remaining > 0 and i < len(state):
        st = state[i]
        if st["complete"]:
            i += 1
            continue
        room = round(st["target"] - st["received"], 2)
        take = min(room, remaining)
        allocations.append((i, take, False))
        remaining = round(remaining - take, 2)
        if take >= room:
            completed.append(i)
        i += 1
    if remaining > 0 and state:
        allocations.append((len(state) - 1, remaining, True))
    return allocations, completed


# Legacy current_stage value -> milestone anchor, and the work stage to
# fall forward to when that anchor no longer exists on the schedule.
_LEGACY_STAGE_ANCHOR = {
    "payment_10": "award",
    "payment_60": "after_seal_sign",
    "payment_30": "after_fabrication",
}
_LEGACY_STAGE_NEXT_WORK = {
    "payment_10": "drafting",
    "payment_60": "fabrication",
    "payment_30": "delivery",
}


async def _ensure_milestones(
    session: AsyncSession, pipeline: AwardPipeline
) -> list[PipelineMilestone]:
    """Seed the schedule for pipelines that predate it, and translate a
    legacy current_stage to its milestone key. Idempotent: pipelines
    that already have rows are untouched."""
    rows = await _load_milestones(session, pipeline.id)
    if not rows:
        # Preserve sent status from the legacy gate stamps, so a legacy
        # pipeline mid-flight keeps its sent/received gates as
        # sent/received milestones.
        legacy_stamps = {
            "award": (
                pipeline.pay10_email_sent_at,
                pipeline.pay10_received_at,
                pipeline.pay10_received_by,
                pipeline.pay10_inv_sent_at,
                pipeline.pay10_inv_sent_to,
            ),
            "after_seal_sign": (
                pipeline.pay60_email_sent_at,
                pipeline.pay60_received_at,
                pipeline.pay60_received_by,
                pipeline.pay60_inv_sent_at,
                pipeline.pay60_inv_sent_to,
            ),
            "after_fabrication": (
                pipeline.pay30_email_sent_at,
                pipeline.pay30_received_at,
                pipeline.pay30_received_by,
                pipeline.pay30_inv_sent_at,
                pipeline.pay30_inv_sent_to,
            ),
        }
        for i, (anchor, label, pct) in enumerate(DEFAULT_MILESTONES):
            email_sent, received, received_by, inv_sent, inv_to = legacy_stamps[anchor]
            row = PipelineMilestone(
                pipeline_id=pipeline.id,
                key=f"m{i + 1}",
                anchor=anchor,
                label=label,
                percent=pct,
                seq=i,
                email_sent_at=email_sent,
                received_at=received,
                received_by=received_by,
                inv_sent_at=inv_sent,
                inv_sent_to=inv_to,
            )
            session.add(row)
            rows.append(row)
        await session.flush()
    if pipeline.current_stage in _LEGACY_STAGE_ANCHOR:
        anchor = _LEGACY_STAGE_ANCHOR[pipeline.current_stage]
        match = next((m for m in rows if m.anchor == anchor), None)
        pipeline.current_stage = (
            _milestone_stage_key(match)
            if match is not None
            else _LEGACY_STAGE_NEXT_WORK[pipeline.current_stage]
        )
        await session.flush()
    return rows


def _advance_key(
    order: list[str],
    current: str,
    milestones_by_key: dict[str, PipelineMilestone],
) -> str:
    """Next stage after ``current`` in dynamic order, skipping payment
    milestones already received. The skip matters after an EOR reject
    returns the pipeline to drafting: the already-received payments
    ahead of drafting must not block re-advance."""
    if current == "completed":
        return "completed"
    try:
        idx = order.index(current)
    except ValueError:
        return "completed"
    for key in order[idx + 1 :]:
        milestone = milestones_by_key.get(key)
        if milestone is not None and milestone.received_at is not None:
            continue
        return key
    return "completed"


async def get_or_create_pipeline(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID | None
) -> AwardPipeline:
    await _ensure_pipeline_schema(session)
    pipeline = (
        await session.execute(
            select(AwardPipeline).where(AwardPipeline.project_id == project_id)
        )
    ).scalar_one_or_none()
    if pipeline is not None:
        await _ensure_milestones(session, pipeline)
        return pipeline
    project = await _get_project(session, project_id)
    pipeline = AwardPipeline(project_id=project_id, current_stage="payment_10")
    session.add(pipeline)
    await session.flush()
    await _log(session, pipeline, "Project awarded — post-award pipeline started", actor_id)
    # OE-DELIVERY 2026-10-22: NO auto email on pipeline creation. Gate
    # emails are deliberate: the "Send {gate}% Invoice to Accountant"
    # popup (send_invoice_email) is the only sender.
    await _ensure_milestones(session, pipeline)
    await session.flush()
    return pipeline


def _stage_completed_at(pipeline: AwardPipeline, key: str) -> datetime | None:
    return {
        "payment_10": pipeline.pay10_received_at,
        "drafting": pipeline.drafting_completed_at,
        "shop_drawings": pipeline.client_approved_at,
        "seal_sign": pipeline.seal_completed_at,
        "payment_60": pipeline.pay60_received_at,
        "fabrication": pipeline.fab_completed_at,
        "payment_30": pipeline.pay30_received_at,
        "delivery": pipeline.delivered_at,
        "feedback": pipeline.feedback_sent_at,
    }.get(key)


# ── Review rounds (OE-DELIVERY 2026-10-26) ─────────────────────────────
# Outcomes that OPEN a new round on their stage. A stage with no such
# rows is on round 1.
_ROUND_OPENING_OUTCOMES = ("revision_requested", "eor_returned")

_REVIEWABLE_STAGES = ("drafting", "shop_drawings", "seal_sign")


async def _current_round(
    session: AsyncSession, pipeline_id: uuid.UUID, stage: str
) -> int:
    rows = (
        await session.execute(
            select(PipelineRevision).where(
                PipelineRevision.pipeline_id == pipeline_id,
                PipelineRevision.stage == stage,
                PipelineRevision.outcome.in_(_ROUND_OPENING_OUTCOMES),
            )
        )
    ).scalars().all()
    return 1 + len(rows)


async def build_view(
    session: AsyncSession, project: Project, pipeline: AwardPipeline
) -> PipelineView:
    # OE-DELIVERY 2026-10-27: the stage list is dynamic - work stages in
    # fixed order with payment milestones woven in by anchor.
    milestones = await _load_milestones(session, pipeline.id)
    # Partial receipts (OE-DELIVERY 2026-10-27): received/balance/excess
    # per milestone. A partially received milestone is in-progress, not
    # done - only received_at marks a stage done in the loop below.
    receipts_by_milestone = await _load_receipts(session, pipeline.id)
    receipt_summary = {
        mid: _receipt_sums(rows) for mid, rows in receipts_by_milestone.items()
    }
    milestones_by_key = {_milestone_stage_key(m): m for m in milestones}
    order = _dynamic_order(milestones)
    current = pipeline.current_stage
    if current == "completed":
        current_idx = len(order)
    elif current in order:
        current_idx = order.index(current)
    else:
        # Defensive: an unknown current_stage must never crash the view.
        current_idx = len(order)

    stages: list[PipelineStageOut] = []
    done_count = 0
    for idx, key in enumerate(order):
        milestone = milestones_by_key.get(key)
        if milestone is not None:
            # A received milestone is done even when it sits ahead of
            # the current stage (EOR reject returns to drafting while
            # the drafting-anchored payment is already received).
            if milestone.received_at is not None:
                state = "done"
                done_count += 1
            elif idx == current_idx:
                state = "current"
            else:
                state = "upcoming"
            stages.append(
                PipelineStageOut(
                    key=key,
                    label=f"Payment {milestone.percent}% - {milestone.label}",
                    state=state,
                    completed_at=milestone.received_at,
                    milestone_id=milestone.id,
                    percent=milestone.percent,
                    milestone_label=milestone.label,
                    amount=_gate_amount(project, milestone.percent),
                    email_sent_at=milestone.email_sent_at,
                    received_at=milestone.received_at,
                    inv_sent_at=milestone.inv_sent_at,
                    inv_sent_to=milestone.inv_sent_to,
                )
            )
            continue
        if key == "drafting" and pipeline.drafting_skipped:
            state = "skipped" if idx <= current_idx else "upcoming"
            if idx < current_idx:
                done_count += 1
        elif idx < current_idx:
            state = "done"
            done_count += 1
        elif idx == current_idx:
            state = "current"
        else:
            state = "upcoming"
        stages.append(
            PipelineStageOut(
                key=key,
                label=STAGE_LABELS[key],
                state=state,
                completed_at=_stage_completed_at(pipeline, key),
            )
        )
    if current == "completed":
        done_count = len(order)
    progress = round(done_count / len(order) * 100) if order else 0

    activity_rows = (
        await session.execute(
            select(PipelineActivity)
            .where(PipelineActivity.pipeline_id == pipeline.id)
            .order_by(PipelineActivity.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    sends = await _load_sends(session, pipeline)

    revision_rows = (
        await session.execute(
            select(PipelineRevision)
            .where(PipelineRevision.pipeline_id == pipeline.id)
            .order_by(PipelineRevision.created_at.asc())
        )
    ).scalars().all()
    current_rounds = {
        st: 1
        + sum(
            1
            for r in revision_rows
            if r.stage == st and r.outcome in _ROUND_OPENING_OUTCOMES
        )
        for st in _REVIEWABLE_STAGES
    }

    actor_names: dict[uuid.UUID, str] = {}
    actor_ids = {r.actor_id for r in activity_rows if r.actor_id} | {
        r.created_by for r in revision_rows if r.created_by
    }
    if actor_ids:
        from app.modules.users.models import User

        users = (
            await session.execute(select(User).where(User.id.in_(actor_ids)))
        ).scalars().all()
        actor_names = {u.id: (u.full_name or u.email) for u in users}

    return PipelineView(
        project_id=project.id,
        project_name=project.name,
        client_name=await _client_name(session, project),
        contract_value=project.contract_value,
        currency=project.currency or "",
        gate_amounts={
            "10": _gate_amount(project, 10),
            "60": _gate_amount(project, 60),
            "30": _gate_amount(project, 30),
        },
        current_stage=current,
        progress_pct=progress,
        stages=stages,
        pay10_email_sent_at=pipeline.pay10_email_sent_at,
        pay10_received_at=pipeline.pay10_received_at,
        pay10_inv_sent_at=pipeline.pay10_inv_sent_at,
        pay10_inv_sent_to=pipeline.pay10_inv_sent_to,
        drafting_skipped=pipeline.drafting_skipped,
        drafting_completed_at=pipeline.drafting_completed_at,
        shop_title=pipeline.shop_title,
        shop_file_name=pipeline.shop_file_name,
        shop_sent_at=pipeline.shop_sent_at,
        client_approved_at=pipeline.client_approved_at,
        pay60_email_sent_at=pipeline.pay60_email_sent_at,
        pay60_received_at=pipeline.pay60_received_at,
        pay60_inv_sent_at=pipeline.pay60_inv_sent_at,
        pay60_inv_sent_to=pipeline.pay60_inv_sent_to,
        seal_completed_at=pipeline.seal_completed_at,
        fab_vendor=pipeline.fab_vendor,
        fab_start_date=pipeline.fab_start_date,
        fab_expected_date=pipeline.fab_expected_date,
        fab_progress=pipeline.fab_progress,
        fab_status=pipeline.fab_status,
        fab_completed_at=pipeline.fab_completed_at,
        pay30_email_sent_at=pipeline.pay30_email_sent_at,
        pay30_received_at=pipeline.pay30_received_at,
        pay30_inv_sent_at=pipeline.pay30_inv_sent_at,
        pay30_inv_sent_to=pipeline.pay30_inv_sent_to,
        del_shipment_ref=pipeline.del_shipment_ref,
        del_tracking_number=pipeline.del_tracking_number,
        del_carrier=pipeline.del_carrier,
        del_destination=pipeline.del_destination,
        del_eta=pipeline.del_eta,
        del_status=pipeline.del_status,
        delivered_at=pipeline.delivered_at,
        feedback_sent_at=pipeline.feedback_sent_at,
        feedback_email=pipeline.feedback_email,
        feedback_unlock_at=(
            pipeline.delivered_at + timedelta(days=30)
            if pipeline.delivered_at
            else None
        ),
        feedback_available=(
            pipeline.current_stage == "feedback"
            and pipeline.delivered_at is not None
            and _now() >= pipeline.delivered_at + timedelta(days=30)
        ),
        sends=sends,
        activity=[
            PipelineActivityOut(
                id=r.id,
                text=r.text,
                actor_name=actor_names.get(r.actor_id) if r.actor_id else None,
                created_at=r.created_at,
            )
            for r in activity_rows
        ],
        revisions=[
            PipelineRevisionOut(
                id=r.id,
                stage=r.stage,
                round_no=r.round_no,
                outcome=r.outcome,
                comments=r.comments,
                actor_name=actor_names.get(r.created_by)
                if r.created_by
                else None,
                created_at=r.created_at,
            )
            for r in revision_rows
        ],
        current_rounds=current_rounds,
        milestones=[
            PipelineMilestoneOut(
                id=m.id,
                key=m.key,
                anchor=m.anchor,
                anchor_label=MILESTONE_ANCHORS[m.anchor][0],
                label=m.label,
                percent=m.percent,
                seq=m.seq,
                amount=_gate_amount(project, m.percent),
                email_sent_at=m.email_sent_at,
                received_at=m.received_at,
                inv_sent_at=m.inv_sent_at,
                inv_sent_to=m.inv_sent_to,
                is_award=m.anchor == "award",
                is_sent=(
                    m.email_sent_at is not None
                    or m.received_at is not None
                    or len(receipts_by_milestone.get(m.id, [])) > 0
                ),
                received_percent=receipt_summary.get(m.id, (0.0, 0.0))[0],
                balance_percent=round(
                    m.percent - receipt_summary.get(m.id, (0.0, 0.0))[0], 2
                ),
                excess_percent=receipt_summary.get(m.id, (0.0, 0.0))[1],
                receipts=[
                    PipelineReceiptOut(
                        id=r.id,
                        milestone_id=r.milestone_id,
                        percent=r.percent,
                        note=r.note,
                        is_excess=r.is_excess,
                        seq=r.seq,
                        created_at=r.created_at,
                    )
                    for r in receipts_by_milestone.get(m.id, [])
                ],
            )
            for m in sorted(
                milestones,
                key=lambda r: order.index(_milestone_stage_key(r))
                if _milestone_stage_key(r) in order
                else len(order),
            )
        ],
    )


async def get_pipeline_view(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID | None
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    return await build_view(session, project, pipeline)


def _require_stage(pipeline: AwardPipeline, expected: str, action: str) -> None:
    if pipeline.current_stage != expected:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot {action}: pipeline is at stage "
            f"'{STAGE_LABELS.get(pipeline.current_stage, pipeline.current_stage)}'",
        )


# ── Actions ───────────────────────────────────────────────────────────


def _sync_legacy_payment_columns(
    pipeline: AwardPipeline, milestone: PipelineMilestone
) -> None:
    """Mirror a milestone's stamps onto the legacy pay*_ columns when
    the milestone sits on a legacy anchor, so older reads keep working."""
    suffix = LEGACY_ANCHOR_COLUMNS.get(milestone.anchor)
    if suffix is None:
        return
    setattr(pipeline, f"pay{suffix}_email_sent_at", milestone.email_sent_at)
    setattr(pipeline, f"pay{suffix}_received_at", milestone.received_at)
    setattr(pipeline, f"pay{suffix}_received_by", milestone.received_by)
    setattr(pipeline, f"pay{suffix}_inv_sent_at", milestone.inv_sent_at)
    setattr(pipeline, f"pay{suffix}_inv_sent_to", milestone.inv_sent_to)


async def _resolve_milestone(
    session: AsyncSession,
    pipeline: AwardPipeline,
    milestone_id: uuid.UUID | None,
    gate: int | None,
    action: str,
) -> PipelineMilestone:
    """Resolve the milestone an action targets: by id (current form),
    or by legacy gate percent (10/60/30 -> legacy anchor)."""
    milestones = await _load_milestones(session, pipeline.id)
    if milestone_id is not None:
        match = next((m for m in milestones if m.id == milestone_id), None)
        if match is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Payment milestone not found"
            )
        return match
    if gate in (10, 60, 30):
        anchor = {10: "award", 60: "after_seal_sign", 30: "after_fabrication"}[gate]
        match = next((m for m in milestones if m.anchor == anchor), None)
        if match is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"No payment milestone for the {gate}% gate on this schedule",
            )
        return match
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Pass a milestone_id to {action}",
    )


async def mark_payment_received(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    milestone_id: uuid.UUID | None = None,
    gate: int | None = None,
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    milestone = await _resolve_milestone(
        session, pipeline, milestone_id, gate, "mark payment received"
    )
    _require_stage(
        pipeline,
        _milestone_stage_key(milestone),
        f"mark {milestone.percent}% payment received",
    )
    milestone.received_at = _now()
    milestone.received_by = actor_id
    _sync_legacy_payment_columns(pipeline, milestone)
    milestones = await _load_milestones(session, pipeline.id)
    order = _dynamic_order(milestones)
    by_key = {_milestone_stage_key(m): m for m in milestones}
    pipeline.current_stage = _advance_key(
        order, _milestone_stage_key(milestone), by_key
    )
    await _log(
        session,
        pipeline,
        f"{milestone.percent}% payment received - {milestone.label} released",
        actor_id,
    )
    await session.flush()
    return await build_view(session, project, pipeline)


async def _completion_email_recipients(
    session: AsyncSession, project: Project, milestone: PipelineMilestone
) -> list[str]:
    """Completion email recipients: project team members with emails,
    plus the Accounts user recorded on the milestone's invoice email
    when one resolves. Best-effort throughout - an empty list is a
    warning at the caller, never an error."""
    emails: list[str] = []
    try:
        from app.modules.teams.models import Team, TeamMembership
        from app.modules.users.models import User

        team_ids = (
            await session.execute(
                select(Team.id).where(Team.project_id == project.id)
            )
        ).scalars().all()
        if team_ids:
            user_ids = (
                await session.execute(
                    select(TeamMembership.user_id).where(
                        TeamMembership.team_id.in_(team_ids)
                    )
                )
            ).scalars().all()
            if user_ids:
                users = (
                    await session.execute(
                        select(User).where(
                            User.id.in_(user_ids), User.is_active == True  # noqa: E712
                        )
                    )
                ).scalars().all()
                emails.extend([u.email for u in users if u.email])
    except Exception:  # noqa: BLE001 - recipient lookup is best-effort
        logger.warning("pipeline: team recipient lookup failed", exc_info=True)
    inv_to = (milestone.inv_sent_to or "").strip()
    if inv_to:
        if "@" in inv_to:
            emails.append(inv_to)
        else:
            try:
                from app.modules.users.models import User

                user = (
                    await session.execute(
                        select(User).where(
                            User.full_name == inv_to, User.is_active == True  # noqa: E712
                        )
                    )
                ).scalar_one_or_none()
                if user is not None and user.email:
                    emails.append(user.email)
            except Exception:  # noqa: BLE001 - best-effort
                logger.warning(
                    "pipeline: accounts recipient lookup failed", exc_info=True
                )
    seen: set[str] = set()
    out: list[str] = []
    for address in emails:
        key = address.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(address.strip())
    return out


async def _send_completion_email(
    session: AsyncSession,
    project: Project,
    pipeline: AwardPipeline,
    milestone: PipelineMilestone,
    next_label: str | None,
    actor_id: uuid.UUID,
) -> None:
    """Automatic email when a milestone's target is fully received.

    This is the ONE automatic email in the receipts feature - gate
    invoice emails stay manual popup sends. Never raises: a failed
    email must not fail the receipt save that already completed.
    """
    try:
        from app.core.email.service import EmailMessage, get_email_service

        recipients = await _completion_email_recipients(session, project, milestone)
        if not recipients:
            logger.warning(
                "pipeline: no recipients for %s completion email",
                milestone.key,
            )
            return
        pct = milestone.percent
        client_name = await _client_name(session, project) or "—"
        contract_text = project.contract_value or "—"
        from app.config import get_settings

        project_url = f"{get_settings().resolved_frontend_url}/projects/{project.id}"
        logo = _logo_attachment()
        if logo is not None:
            header_inner = (
                f'<img src="cid:{_LOGO_CID}" alt="Florida Steel" height="44" '
                f'style="display:block;height:44px;border:0">'
            )
        else:
            header_inner = (
                '<span style="font-family:Arial,sans-serif;font-size:24px;'
                'font-weight:bold"><span style="color:#c8102e">FLORIDA</span> '
                '<span style="color:#3a3f46">STEEL</span></span>'
            )
        next_sentence = (
            f" Next step: {html.escape(next_label)} can begin."
            if next_label
            else ""
        )
        body = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f3f5f8">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f5f8">
  <tr><td align="center" style="padding:24px 12px">
    <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #d9dee7;border-radius:10px">
      <tr><td style="background:#ffffff;padding:18px 24px 12px;border-bottom:3px solid #c8102e">
        {header_inner}
        <div style="font-family:Arial,sans-serif;font-size:11.5px;color:#6b7280;letter-spacing:.04em;margin-top:8px">PAYMENT COMPLETE · POST-AWARD PIPELINE</div>
      </td></tr>
      <tr><td style="padding:20px 24px;font-family:Arial,sans-serif;color:#1a1a1a">
        <div style="font-size:15px">Hello team,</div>
        <p style="font-size:14px;line-height:1.55;color:#333333;margin:12px 0 0">The <b>{pct}% {html.escape(milestone.label)} payment</b> for the project below is fully received.{next_sentence}</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13.5px;margin-top:14px">
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666;width:150px">Project</td><td style="padding:8px 10px;border:1px solid #e2e6ee"><b>{html.escape(project.name)}</b></td></tr>
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666">Client</td><td style="padding:8px 10px;border:1px solid #e2e6ee">{html.escape(client_name)}</td></tr>
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666">Contract value</td><td style="padding:8px 10px;border:1px solid #e2e6ee">{html.escape(contract_text)}</td></tr>
        </table>
      </td></tr>
      <tr><td style="padding:2px 24px 20px;font-family:Arial,sans-serif">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td style="background:#2563eb;border-radius:7px"><a href="{html.escape(project_url)}" style="display:inline-block;padding:10px 20px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#ffffff;text-decoration:none">Open Project in ERP</a></td>
        </tr></table>
        <div style="border-top:1px solid #e2e6ee;margin-top:18px;padding-top:12px;font-size:12px;color:#888888">Sent via OpenConstructionERP · Post-Award Pipeline</div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>
"""
        subject = f"{milestone.label} {pct}% complete — {project.name}"
        service = get_email_service()
        for address in recipients:
            try:
                result = await service.send(
                    EmailMessage(
                        to=address,
                        subject=subject,
                        html_body=body,
                        tags=["award_pipeline_completion"],
                        attachments=[logo] if logo is not None else [],
                    )
                )
                if not result.ok:
                    logger.warning(
                        "pipeline: completion email to %s failed", address
                    )
            except Exception:  # noqa: BLE001 - per-recipient best-effort
                logger.warning(
                    "pipeline: completion email to %s failed", address, exc_info=True
                )
        await _log(
            session,
            pipeline,
            f"{pct}% payment complete - {milestone.label} completion email sent",
            actor_id,
        )
    except Exception:  # noqa: BLE001 - never fail the receipt save
        logger.warning("pipeline: completion email failed", exc_info=True)


async def _complete_milestones(
    session: AsyncSession,
    project: Project,
    pipeline: AwardPipeline,
    order: list[str],
    by_key: dict[str, PipelineMilestone],
    milestones_to_complete: list[PipelineMilestone],
    actor_id: uuid.UUID,
) -> None:
    """Shared milestone-completion path for receipts (record + edit).

    OE-DELIVERY 2026-10-27 (receipt edit): extracted verbatim from
    record_receipt so an edit that reaches the target completes
    exactly the same way - received stamp, legacy column sync,
    advance when the milestone is the current stage, activity log,
    and one completion email per milestone, only on the transition
    to complete. Milestones already complete are skipped.
    """
    completed_milestones: list[PipelineMilestone] = []
    for m in milestones_to_complete:
        if m.received_at is not None:
            continue
        m.received_at = _now()
        m.received_by = actor_id
        _sync_legacy_payment_columns(pipeline, m)
        if pipeline.current_stage == _milestone_stage_key(m):
            pipeline.current_stage = _advance_key(
                order, _milestone_stage_key(m), by_key
            )
        await _log(
            session,
            pipeline,
            f"{m.percent}% payment fully received - {m.label}",
            actor_id,
        )
        completed_milestones.append(m)
    await session.flush()
    for m in completed_milestones:
        idx = order.index(_milestone_stage_key(m))
        next_key = order[idx + 1] if idx + 1 < len(order) else None
        if next_key is None:
            next_label = None
        elif next_key in by_key:
            nxt = by_key[next_key]
            next_label = f"Payment {nxt.percent}% - {nxt.label}"
        else:
            next_label = STAGE_LABELS.get(next_key)
        await _send_completion_email(
            session, project, pipeline, m, next_label, actor_id
        )
    await session.flush()


async def record_receipt(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    milestone_id: uuid.UUID,
    data: PipelineReceiptIn,
) -> PipelineView:
    """Record one partial receipt against a payment milestone.

    Money arrives in unpredictable amounts, so any positive percent is
    accepted - there are no pre-defined parts. The receipt fills the
    milestone up to its target; any remainder carries forward to the
    next incomplete milestone in schedule order, and past the final
    milestone it stays as a flagged excess row, never dropped. A
    milestone that reaches its target completes exactly as "Mark
    Payment Received" does (advance when it is the current stage),
    and one completion email goes out per milestone completed by this
    receipt - only on the transition to complete, never per receipt.
    """
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    milestones = await _load_milestones(session, pipeline.id)
    milestone = next((m for m in milestones if m.id == milestone_id), None)
    if milestone is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Payment milestone not found"
        )
    if milestone.received_at is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Payment milestone is already complete"
        )
    if data.percent is None or data.percent <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Receipt percent must be greater than 0"
        )
    order = _dynamic_order(milestones)
    by_key = {_milestone_stage_key(m): m for m in milestones}
    payment_order = [by_key[k] for k in order if k in by_key]
    receipts_by_milestone = await _load_receipts(session, pipeline.id)
    state = [
        {
            "target": float(m.percent),
            "received": _receipt_sums(receipts_by_milestone.get(m.id, []))[0],
            "complete": m.received_at is not None,
        }
        for m in payment_order
    ]
    target_index = next(
        i for i, m in enumerate(payment_order) if m.id == milestone_id
    )
    allocations, completed_indices = _plan_receipts(
        state, target_index, float(data.percent)
    )
    note = (data.note or "").strip() or None
    for pos, (mi, pct, is_excess) in enumerate(allocations):
        m = payment_order[mi]
        rows = receipts_by_milestone.setdefault(m.id, [])
        seq = max([r.seq for r in rows], default=-1) + 1
        if is_excess:
            row_note = note or f"Excess payment beyond the {m.percent}% target"
        elif pos == 0:
            row_note = note
        else:
            row_note = f"Carried forward from {milestone.label}"
            if note:
                row_note = f"{row_note} - {note}"
        row = PipelineReceipt(
            milestone_id=m.id,
            percent=pct,
            note=row_note,
            recorded_by=actor_id,
            is_excess=is_excess,
            seq=seq,
        )
        session.add(row)
        rows.append(row)
    await _complete_milestones(
        session,
        project,
        pipeline,
        order,
        by_key,
        [payment_order[mi] for mi in completed_indices],
        actor_id,
    )
    return await build_view(session, project, pipeline)


async def update_receipt(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    milestone_id: uuid.UUID,
    receipt_id: uuid.UUID,
    data: PipelineReceiptUpdate,
) -> PipelineView:
    """Edit one recorded receipt against a payment milestone.

    OE-DELIVERY 2026-10-27 (receipt edit): percent and/or note can
    change; omitted fields keep their value. Guards keep the receipt
    chain consistent:
      * the milestone must be incomplete - completed milestones lock
        their receipts, which also covers excess rows (an excess row
        only ever exists on a milestone already filled to target);
      * excess rows and carried-forward rows cannot be edited
        directly - carried rows are derived from an earlier
        milestone's overpayment, identified by their
        "Carried forward from ..." note, the only marker the record
        path stores;
      * the edit must not push the milestone past its target - an
        increase beyond the room is rejected, and the extra money
        should be recorded as a new receipt instead (which runs the
        normal carry-forward plan).
    A completed milestone cannot be un-completed by an edit: edits
    are refused once received_at is set, so a spill recorded on a
    completed milestone (and its carried rows downstream) cannot be
    corrected through editing - there is no delete path. An edit
    that reaches the target runs the shared completion path (email
    + advance when current), exactly as a record does.
    """
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    milestones = await _load_milestones(session, pipeline.id)
    milestone = next((m for m in milestones if m.id == milestone_id), None)
    if milestone is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Payment milestone not found"
        )
    if milestone.received_at is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Payment milestone is already complete"
        )
    receipts_by_milestone = await _load_receipts(session, pipeline.id)
    rows = receipts_by_milestone.get(milestone_id, [])
    row = next((r for r in rows if r.id == receipt_id), None)
    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Receipt not found"
        )
    if row.is_excess:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Excess receipts cannot be edited"
        )
    if (row.note or "").startswith("Carried forward from "):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Carried-forward receipts cannot be edited directly",
        )
    new_percent = float(data.percent) if data.percent is not None else row.percent
    if new_percent <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Receipt percent must be greater than 0"
        )
    received, _excess = _receipt_sums(rows)
    new_received = round(received - row.percent + new_percent, 2)
    if new_received > float(milestone.percent):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Edited receipt would exceed the milestone target",
        )
    row.percent = new_percent
    if data.note is not None:
        row.note = (data.note or "").strip() or None
    order = _dynamic_order(milestones)
    by_key = {_milestone_stage_key(m): m for m in milestones}
    if new_received >= float(milestone.percent):
        await _complete_milestones(
            session, project, pipeline, order, by_key, [milestone], actor_id
        )
    else:
        await session.flush()
    return await build_view(session, project, pipeline)


async def save_schedule(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: SaveScheduleIn,
) -> PipelineView:
    """Replace the pipeline's payment schedule (editor Save).

    Rules, all enforced here (the editor mirrors them, but the server
    is the authority):
      * 3-5 rows total; exactly one award row, percent 10, first.
      * Remainder anchors from the allowed set only - never at or
        after delivery, so 100% is always collected before delivery.
      * Percents sum to exactly 100.
      * Sent rows (email or received) keep their percent, label and
        anchor, and cannot be deleted.
      * The current payment stage can neither be deleted nor moved:
        moving it could strand a work stage (e.g. fabrication) behind
        the current position, and deleting it would dangle
        current_stage.
      * After the edit, every unsent milestone must sit at or after the
        current stage, and every work stage before the current stage
        must be done or skipped - otherwise a payment could become
        unreachable or a work stage silently skipped.
    New rows get fresh keys (m<N>, never reused); surviving rows keep
    their key, so current_stage keeps pointing at the same milestone.
    """
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    existing = await _load_milestones(session, pipeline.id)
    by_id = {m.id: m for m in existing}
    # Partial receipts lock a milestone exactly like a sent one.
    receipts_by_milestone = await _load_receipts(session, pipeline.id)

    rows = data.milestones
    if not MIN_MILESTONES <= len(rows) <= MAX_MILESTONES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Schedule needs {MIN_MILESTONES}-{MAX_MILESTONES} milestones",
        )
    award_rows = [r for r in rows if r.anchor == "award"]
    if len(award_rows) != 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Schedule needs exactly one award milestone",
        )
    award_in = award_rows[0]
    if rows[0] is not award_in:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The award milestone must be first",
        )
    if award_in.percent != 10:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "The award milestone is fixed at 10%"
        )
    for r in rows:
        if r.id is not None and r.id not in by_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Unknown milestone in schedule"
            )
        if r.anchor != "award" and r.anchor not in MILESTONE_ANCHORS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Unknown anchor '{r.anchor}'"
            )
        if not r.label.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Each milestone needs a label"
            )
    if sum(r.percent for r in rows) != 100:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Milestone percents must add up to 100%",
        )

    incoming_ids = {r.id for r in rows if r.id is not None}
    current_key = pipeline.current_stage
    current_milestone = next(
        (m for m in existing if _milestone_stage_key(m) == current_key), None
    )
    for m in existing:
        sent = m.email_sent_at is not None or m.received_at is not None
        has_receipts = len(receipts_by_milestone.get(m.id, [])) > 0
        incoming = next((r for r in rows if r.id == m.id), None)
        if incoming is None:
            if has_receipts:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Cannot delete the milestone '{m.label}' with recorded receipts",
                )
            if sent:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Cannot delete the sent milestone '{m.label}'",
                )
            if current_milestone is not None and m.id == current_milestone.id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Cannot delete the current payment stage",
                )
            continue
        if has_receipts and (
            incoming.percent != m.percent
            or incoming.label.strip() != m.label
            or incoming.anchor != m.anchor
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Cannot change the milestone '{m.label}' with recorded receipts",
            )
        if sent and (
            incoming.percent != m.percent
            or incoming.label.strip() != m.label
            or incoming.anchor != m.anchor
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Cannot change the sent milestone '{m.label}'",
            )
        if (
            current_milestone is not None
            and m.id == current_milestone.id
            and incoming.anchor != m.anchor
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Cannot move the current payment stage",
            )

    # Apply: update surviving rows, delete removed rows, add new rows.
    used_numbers = [
        int(m.key[1:]) for m in existing if m.key.startswith("m") and m.key[1:].isdigit()
    ]
    next_number = max(used_numbers, default=0) + 1
    next_seq = max([m.seq for m in existing], default=-1) + 1
    kept: list[PipelineMilestone] = []
    for incoming in rows:
        if incoming.id is not None and incoming.id in by_id:
            m = by_id[incoming.id]
            m.anchor = incoming.anchor
            m.label = incoming.label.strip()
            m.percent = incoming.percent
            kept.append(m)
        else:
            m = PipelineMilestone(
                pipeline_id=pipeline.id,
                key=f"m{next_number}",
                anchor=incoming.anchor,
                label=incoming.label.strip(),
                percent=incoming.percent,
                seq=next_seq,
            )
            next_number += 1
            next_seq += 1
            session.add(m)
            kept.append(m)
    for m in existing:
        if m.id not in incoming_ids:
            await session.delete(m)
    await session.flush()

    # Order invariants on the NEW schedule (skipped once completed).
    if pipeline.current_stage != "completed":
        order = _dynamic_order(kept)
        if current_key not in order:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "The current stage is missing from the new schedule",
            )
        current_idx = order.index(current_key)
        by_key = {_milestone_stage_key(m): m for m in kept}
        for idx, key in enumerate(order):
            m = by_key.get(key)
            if m is not None:
                if idx < current_idx and m.received_at is None:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "Cannot move an unpaid milestone before the current stage",
                    )
            elif idx < current_idx:
                if _stage_completed_at(pipeline, key) is None and not (
                    key == "drafting" and pipeline.drafting_skipped
                ):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "The new schedule would skip an unfinished work stage",
                    )

    await _log(session, pipeline, "Payment schedule updated", actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)


async def skip_drafting(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "drafting", "skip engineering / drafting")
    pipeline.drafting_skipped = True
    pipeline.drafting_completed_at = _now()
    pipeline.drafting_completed_by = actor_id
    milestones = await _load_milestones(session, pipeline.id)
    pipeline.current_stage = _advance_key(
        _dynamic_order(milestones),
        "drafting",
        {_milestone_stage_key(m): m for m in milestones},
    )
    await _log(session, pipeline, "Engineering / Drafting skipped by Coordinator", actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)


async def complete_drafting(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "drafting", "complete engineering / drafting")
    pipeline.drafting_completed_at = _now()
    pipeline.drafting_completed_by = actor_id
    milestones = await _load_milestones(session, pipeline.id)
    pipeline.current_stage = _advance_key(
        _dynamic_order(milestones),
        "drafting",
        {_milestone_stage_key(m): m for m in milestones},
    )
    session.add(
        PipelineRevision(
            pipeline_id=pipeline.id,
            stage="drafting",
            round_no=await _current_round(session, pipeline.id, "drafting"),
            outcome="approved",
            created_by=actor_id,
        )
    )
    await _log(session, pipeline, "Engineering / Drafting completed", actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)


async def _load_sends(
    session: AsyncSession, pipeline: AwardPipeline
) -> list[PipelineSendOut]:
    """Pipeline sends joined with their transmittal + recipient tracking."""
    from app.modules.file_transmittals.models import (
        FileTransmittal,
        FileTransmittalItem,
        FileTransmittalRecipient,
    )

    rows = (
        await session.execute(
            select(PipelineSend)
            .where(PipelineSend.pipeline_id == pipeline.id)
            .order_by(PipelineSend.created_at.asc())
        )
    ).scalars().all()
    out: list[PipelineSendOut] = []
    for row in rows:
        transmittal = await session.get(FileTransmittal, row.transmittal_id)
        recipients = (
            await session.execute(
                select(FileTransmittalRecipient)
                .where(FileTransmittalRecipient.transmittal_id == row.transmittal_id)
                .order_by(FileTransmittalRecipient.created_at.asc())
            )
        ).scalars().all()
        recipient = recipients[0] if recipients else None
        items = (
            await session.execute(
                select(FileTransmittalItem)
                .where(FileTransmittalItem.transmittal_id == row.transmittal_id)
                .order_by(FileTransmittalItem.sort_order.asc())
            )
        ).scalars().all()
        out.append(
            PipelineSendOut(
                id=row.id,
                stage=row.stage,
                transmittal_id=row.transmittal_id,
                transmittal_number=transmittal.number if transmittal else None,
                subject=transmittal.subject if transmittal else None,
                recipient_email=recipient.email if recipient else None,
                recipient_name=recipient.display_name if recipient else None,
                recipient_role=recipient.role if recipient else None,
                recipient_count=max(1, len(recipients)),
                file_names=[i.canonical_name_snapshot for i in items],
                sent_at=transmittal.sent_at if transmittal else row.created_at,
                opened_at=next((r.opened_at for r in recipients if r.opened_at), None),
                viewed_at=next((r.viewed_at for r in recipients if r.viewed_at), None),
                view_count=sum(r.view_count or 0 for r in recipients),
                acknowledged_at=next(
                    (r.acknowledged_at for r in recipients if r.acknowledged_at), None
                ),
            )
        )
    return out


async def send_files(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: PipelineSendIn,
) -> PipelineView:
    """Create + send a REAL File Transmittal from inside the pipeline.

    stage 'drafting'    — from the Drafting stage (reason: for_review)
    stage 'shop_prep'   — Shop Drawings Step 1: send FOR shop drawing
    stage 'shop_client' — Shop Drawings Step 2: send the finished shop
                          drawings to the client for approval (recipient
                          role forced to 'Client'; requires Step 1 first)
    stage 'seal_sign'   — Seal & Sign: shop drawings sent to the EOR/AOR
                          for seal & sign (reason: for_approval)
    """
    from app.modules.file_transmittals.schemas import (
        TransmittalCreate,
        TransmittalItemCreate,
        TransmittalRecipientCreate,
    )
    from app.modules.file_transmittals.service import TransmittalService

    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)

    default_subjects = {
        "drafting": f"Engineering / Drafting files — {project.name}",
        "shop_prep": f"For shop drawing — {project.name}",
        "shop_client": f"Shop drawings for approval — {project.name}",
        "fabrication": f"Fabrication files — {project.name}",
        "seal_sign": f"For seal & sign — {project.name}",
    }
    if data.stage == "drafting":
        _require_stage(pipeline, "drafting", "send drafting files")
        reason = "for_review"
        role = (data.recipient_role or "Internal").strip() or "Internal"
    elif data.stage == "shop_prep":
        _require_stage(pipeline, "shop_drawings", "send files for shop drawing")
        reason = "for_review"
        role = (data.recipient_role or "Contractor").strip() or "Contractor"
    elif data.stage == "shop_client":
        _require_stage(pipeline, "shop_drawings", "send shop drawings to the client")
        reason = "for_approval"
        role = "Client"
    elif data.stage == "fabrication":
        _require_stage(pipeline, "fabrication", "send fabrication files")
        reason = "for_construction"
        role = (data.recipient_role or "Contractor").strip() or "Contractor"
    elif data.stage == "seal_sign":
        _require_stage(pipeline, "seal_sign", "send drawings for seal & sign")
        reason = "for_approval"
        role = (data.recipient_role or "EOR").strip() or "EOR"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown send stage '{data.stage}'.",
        )

    # Recipients: the multi form (recipients list) puts everyone on ONE
    # transmittal; the panel groups by role, so a group shares one
    # subject/message. The legacy single form keeps working unchanged.
    if data.recipients:
        people = [
            {
                "email": r.email.strip(),
                "name": (r.name or "").strip() or None,
                "role": (
                    "Client"
                    if data.stage == "shop_client"
                    else ((r.role or "").strip() or role)
                ),
            }
            for r in data.recipients
            if r.email and r.email.strip()
        ]
        if not people:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Add at least one recipient with an email."
            )
    else:
        if not (data.recipient_email or "").strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Recipient email is required."
            )
        people = [
            {
                "email": data.recipient_email.strip(),
                "name": (data.recipient_name or "").strip() or None,
                "role": role,
            }
        ]
    who = ", ".join(p["email"] for p in people)
    if len(people) > 2:
        who = f"{people[0]['email']}, {people[1]['email']} +{len(people) - 2} more"

    subject = (data.subject or "").strip() or default_subjects[data.stage]
    try:
        create = TransmittalCreate(
            project_id=project_id,
            subject=subject,
            reason_code=reason,
            notes=(
                (data.message or "").strip()
                or (
                    "Sent from the post-award pipeline ("
                    + STAGE_LABELS.get(pipeline.current_stage, pipeline.current_stage)
                    + ")."
                )
            ),
            items=[
                TransmittalItemCreate(
                    file_kind=f.file_kind,
                    file_id=f.file_id,
                    canonical_name_snapshot=f.name,
                    sort_order=i,
                )
                for i, f in enumerate(data.files)
            ],
            recipients=[
                TransmittalRecipientCreate(
                    email=p["email"],
                    display_name=p["name"],
                    role=p["role"],
                )
                for p in people
            ],
        )
    except Exception as exc:  # pydantic validation (e.g. bad email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid send details: {exc}",
        ) from exc
    svc = TransmittalService(session)
    transmittal = await svc.create_draft(create, sender_id=actor_id)
    transmittal = await svc.send(transmittal.id)

    session.add(
        PipelineSend(
            pipeline_id=pipeline.id,
            project_id=project_id,
            stage=data.stage,
            transmittal_id=transmittal.id,
        )
    )
    file_list = ", ".join(f.name for f in data.files)
    if data.stage == "drafting":
        text = (
            f"Engineering / Drafting files sent to {who} "
            f"(Transmittal {transmittal.number}): {file_list}"
        )
    elif data.stage == "seal_sign":
        text = (
            f"Sent for seal & sign to {who} "
            f"(Transmittal {transmittal.number}): {file_list}"
        )
    elif data.stage == "shop_prep":
        text = (
            f"Sent for shop drawing to {who} "
            f"(Transmittal {transmittal.number}): {file_list}"
        )
    elif data.stage == "fabrication":
        text = (
            f"Fabrication files sent to {who} "
            f"(Transmittal {transmittal.number}): {file_list}"
        )
    else:
        text = (
            "Shop drawings sent to client for approval "
            f"(Transmittal {transmittal.number}): {file_list}"
        )
        pipeline.shop_sent_at = _now()
        pipeline.shop_title = subject
        pipeline.shop_file_name = data.files[0].name
    await _log(session, pipeline, text, actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)


async def record_shop_sent(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID, data: ShopSentIn
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "shop_drawings", "record shop drawings sent")
    pipeline.shop_title = data.title
    pipeline.shop_file_name = data.file_name
    pipeline.shop_sent_at = _now()
    pipeline.shop_sent_by = actor_id
    await _log(
        session, pipeline, f"Shop drawings sent to client — {data.title}", actor_id
    )
    await session.flush()
    return await build_view(session, project, pipeline)


async def client_approved(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "shop_drawings", "mark client approved")
    if pipeline.shop_sent_at is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Record the shop drawings as sent to the client first",
        )
    pipeline.client_approved_at = _now()
    pipeline.client_approved_by = actor_id
    milestones = await _load_milestones(session, pipeline.id)
    pipeline.current_stage = _advance_key(
        _dynamic_order(milestones),
        "shop_drawings",
        {_milestone_stage_key(m): m for m in milestones},
    )
    session.add(
        PipelineRevision(
            pipeline_id=pipeline.id,
            stage="shop_drawings",
            round_no=await _current_round(session, pipeline.id, "shop_drawings"),
            outcome="approved",
            created_by=actor_id,
        )
    )
    await _log(session, pipeline, "Client approved the shop drawings", actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)


async def request_revision(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    stage: str,
    data: RevisionIn,
) -> PipelineView:
    """Ask for changes on the current review stage; the stage stays open.

    Only drafting / shop_drawings take revision requests — payment,
    fabrication, delivery and feedback stages have no review cycle. The
    request opens the next round on that stage; sends stay enabled while
    the stage is current, so revised files go out as new transmittals.
    """
    if stage not in ("drafting", "shop_drawings"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stage '{stage}' has no revision cycle",
        )
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, stage, "request revision")
    round_no = await _current_round(session, pipeline.id, stage)
    session.add(
        PipelineRevision(
            pipeline_id=pipeline.id,
            stage=stage,
            round_no=round_no,
            outcome="revision_requested",
            comments=data.comments,
            created_by=actor_id,
        )
    )
    await _log(
        session,
        pipeline,
        f"Revision requested — {STAGE_LABELS[stage]} (round {round_no})",
        actor_id,
    )
    await session.flush()
    return await build_view(session, project, pipeline)


async def reject_seal(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: RejectSealIn,
) -> PipelineView:
    """EOR refuses to seal: return the pipeline to Engineering/Drafting.

    The seal decision is recorded, then a rework round opens on drafting
    carrying the EOR comments — so the returned stage shows revision
    options instead of a plain reopen. Drafting + shop markers are
    cleared so the re-cycle starts clean (client approval must come
    again, because the drawings will change); payment markers are never
    touched — money already received stays received. Activity history
    is kept.
    """
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "seal_sign", "reject seal & sign")
    seal_round = await _current_round(session, pipeline.id, "seal_sign")
    drafting_round = await _current_round(session, pipeline.id, "drafting")
    session.add(
        PipelineRevision(
            pipeline_id=pipeline.id,
            stage="seal_sign",
            round_no=seal_round,
            outcome="eor_rejected",
            comments=data.comments,
            created_by=actor_id,
        )
    )
    session.add(
        PipelineRevision(
            pipeline_id=pipeline.id,
            stage="drafting",
            round_no=drafting_round,
            outcome="eor_returned",
            comments=data.comments,
            created_by=actor_id,
        )
    )
    pipeline.drafting_completed_at = None
    pipeline.drafting_completed_by = None
    pipeline.shop_title = None
    pipeline.shop_file_name = None
    pipeline.shop_sent_at = None
    pipeline.shop_sent_by = None
    pipeline.client_approved_at = None
    pipeline.client_approved_by = None
    pipeline.current_stage = "drafting"
    await _log(
        session,
        pipeline,
        "EOR rejected — returned to Engineering / Drafting",
        actor_id,
    )
    await session.flush()
    return await build_view(session, project, pipeline)


async def complete_seal_sign(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID
) -> PipelineView:
    """Sealed & signed drawings received back from the EOR/AOR.

    Advances to the next stage in dynamic order (usually the next
    payment milestone, which emails the Accounts team).
    """
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "seal_sign", "complete seal & sign")
    pipeline.seal_completed_at = _now()
    pipeline.seal_completed_by = actor_id
    milestones = await _load_milestones(session, pipeline.id)
    pipeline.current_stage = _advance_key(
        _dynamic_order(milestones),
        "seal_sign",
        {_milestone_stage_key(m): m for m in milestones},
    )
    await _log(
        session, pipeline, "Seal & sign completed by EOR", actor_id
    )
    await session.flush()
    return await build_view(session, project, pipeline)


async def update_fabrication(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID, data: FabricationIn
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "fabrication", "update fabrication")
    if data.status is not None:
        if data.status not in ("started", "in_progress", "completed"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid fabrication status: {data.status}",
            )
        pipeline.fab_status = data.status
    if data.vendor is not None:
        pipeline.fab_vendor = data.vendor
    if data.start_date is not None:
        pipeline.fab_start_date = data.start_date
    if data.expected_date is not None:
        pipeline.fab_expected_date = data.expected_date
    if data.progress is not None:
        pipeline.fab_progress = data.progress
    await session.flush()
    return await build_view(session, project, pipeline)


async def complete_fabrication(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "fabrication", "complete fabrication")
    pipeline.fab_progress = 100
    pipeline.fab_status = "completed"
    pipeline.fab_completed_at = _now()
    pipeline.fab_completed_by = actor_id
    milestones = await _load_milestones(session, pipeline.id)
    pipeline.current_stage = _advance_key(
        _dynamic_order(milestones),
        "fabrication",
        {_milestone_stage_key(m): m for m in milestones},
    )
    await _log(session, pipeline, "Fabrication completed", actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)


async def update_delivery(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID, data: DeliveryIn
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "delivery", "update delivery")
    if data.shipment_ref is not None:
        pipeline.del_shipment_ref = data.shipment_ref
    if data.tracking_number is not None:
        pipeline.del_tracking_number = data.tracking_number
    if data.carrier is not None:
        pipeline.del_carrier = data.carrier
    if data.destination is not None:
        pipeline.del_destination = data.destination
    if data.eta is not None:
        pipeline.del_eta = data.eta
    if data.status is not None:
        if data.status not in ("pending", "dispatched", "in_transit", "arrived"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Invalid delivery status: {data.status}"
            )
        if data.status != pipeline.del_status:
            pipeline.del_status = data.status
            label = {
                "dispatched": "Delivery dispatched",
                "in_transit": "Delivery in transit",
                "arrived": "Delivery arrived at site",
                "pending": "Delivery status reset to pending",
            }[data.status]
            await _log(session, pipeline, label, actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)


async def mark_delivered(
    session: AsyncSession, project_id: uuid.UUID, actor_id: uuid.UUID
) -> PipelineView:
    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "delivery", "mark delivered")
    pipeline.delivered_at = _now()
    pipeline.delivered_by = actor_id
    milestones = await _load_milestones(session, pipeline.id)
    pipeline.current_stage = _advance_key(
        _dynamic_order(milestones),
        "delivery",
        {_milestone_stage_key(m): m for m in milestones},
    )
    await _log(
        session,
        pipeline,
        "Delivered & accepted — feedback stage opens in 30 days",
        actor_id,
    )
    await session.flush()
    return await build_view(session, project, pipeline)


# ── Invoice email (payment gates) ─────────────────────────────────────


async def list_accounts_users(session: AsyncSession) -> list[AccountsUserOut]:
    """Active Accounts-team users for the invoice-email popup."""
    from app.modules.users.models import User

    users = (
        await session.execute(
            select(User)
            .where(User.is_active.is_(True), User.role.ilike("%account%"))
            .order_by(User.full_name.asc())
        )
    ).scalars().all()
    return [
        AccountsUserOut(
            id=u.id,
            name=u.full_name or u.email,
            email=u.email,
            role=u.role,
        )
        for u in users
        if u.email
    ]


_LOGO_CID = "fsftm-logo"


def _logo_attachment():
    """FSFTM brand logo as an inline (CID) email image, or None.

    The PNG ships with the backend at app/core/email/assets/. A missing
    or unreadable file must never break an invoice send — the caller
    falls back to a text wordmark and the email still goes out.
    """
    try:
        from pathlib import Path

        from app.core.email.base import EmailAttachment

        path = (
            Path(__file__).resolve().parents[2]
            / "core"
            / "email"
            / "assets"
            / "fsftm-logo.png"
        )
        return EmailAttachment(
            filename="fsftm-logo.png",
            content=path.read_bytes(),
            content_type="image/png",
            content_id=_LOGO_CID,
        )
    except Exception:  # noqa: BLE001 - logo is decoration, never a blocker
        return None


async def _actor_role_label(session: AsyncSession, actor) -> str:
    """Human label for the acting user's role (custom roles by name)."""
    if actor is None:
        return ""
    role = (actor.role or "").strip()
    if role.startswith("custom_"):
        try:
            from app.modules.users.models import CustomRole

            row = (
                await session.execute(
                    select(CustomRole).where(CustomRole.slug == role)
                )
            ).scalar_one_or_none()
            if row is not None:
                return row.name
        except Exception:  # noqa: BLE001 - label only; fall through
            pass
        role = role[len("custom_") :]
    return role.replace("_", " ").title()


async def send_invoice_email(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: InvoiceEmailIn,
) -> PipelineView:
    """Email ONE Accounts user asking them to invoice the client.

    Triggered by the "Send {pct}% Invoice to Accountant" button + popup
    on a payment milestone. The milestone's percent and label drive the
    popup title, the subject and the body. The ERP creates no invoice -
    Accounts invoices the client externally; this email hands them the
    milestone details.
    """
    from app.core.email.service import EmailMessage, get_email_service
    from app.modules.users.models import User

    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    milestone = await _resolve_milestone(
        session, pipeline, data.milestone_id, data.gate, "send invoice email"
    )
    _require_stage(
        pipeline,
        _milestone_stage_key(milestone),
        f"send {milestone.percent}% invoice email",
    )

    user = await session.get(User, data.user_id)
    if user is None or not user.is_active or not user.email:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Selected user not found, inactive, or has no email address.",
        )

    client_name = await _client_name(session, project) or "—"
    pct = milestone.percent
    amount = _gate_amount(project, pct)
    amount_text = (
        f"{project.currency or ''} {amount:,.2f}".strip() if amount is not None else "—"
    )
    contract_text = project.contract_value or "—"

    actor = await session.get(User, actor_id)
    actor_role = await _actor_role_label(session, actor)
    requested_by = actor_role or "Project team"

    # OE-DELIVERY 2026-10-27-invoice-accounting-team: invoice emails never
    # name a person - the recipient is always addressed as Accounting team.
    greeting_name = "Accounting team"

    now = _now()
    date_text = now.strftime("%d %b %Y")
    stamp_text = now.strftime("%d %b %Y, %I:%M %p")
    # OE-DELIVERY 2026-10-27: the milestone's label is the word ("10%
    # Advance invoice") and its anchor is the blurb ("Advance · On
    # award", "Progress · After Seal & Sign").
    gate_word = milestone.label
    gate_blurb = f"{milestone.label} · {MILESTONE_ANCHORS[milestone.anchor][0]}"

    from app.config import get_settings

    project_url = f"{get_settings().resolved_frontend_url}/projects/{project.id}"

    # Branded template (approved 2026-10-23): white header with the FSFTM
    # logo embedded inline (CID) + red rule, gate/amount summary boxes,
    # details table, the sender's popup message as a note box (only when
    # they typed one), an Open Project button and a reply-with-invoice-
    # number ask. Table layout + inline styles for mail-client safety.
    logo = _logo_attachment()
    if logo is not None:
        header_inner = (
            f'<img src="cid:{_LOGO_CID}" alt="Florida Steel" height="44" '
            f'style="display:block;height:44px;border:0">'
        )
    else:
        header_inner = (
            '<span style="font-family:Arial,sans-serif;font-size:24px;'
            'font-weight:bold"><span style="color:#c8102e">FLORIDA</span> '
            '<span style="color:#3a3f46">STEEL</span></span>'
        )

    custom_message = (data.message or "").strip()
    if custom_message:
        note_text_html = html.escape(custom_message).replace("\n", "<br>")
        note_html = f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;background:#fff8e6;border:1px solid #f0dfa8;border-radius:8px">
          <tr><td style="padding:12px 14px;font-family:Arial,sans-serif">
            <div style="font-size:11px;font-weight:bold;color:#8a6d1a;letter-spacing:.05em">NOTE FROM PROJECT TEAM</div>
            <div style="font-size:13.5px;color:#4a3d10;margin-top:4px">{note_text_html}</div>
          </td></tr>
        </table>"""
    else:
        note_html = ""

    amount_sub = (
        f"of {html.escape(contract_text)} contract" if amount is not None else "&nbsp;"
    )

    body = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f3f5f8">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f5f8">
  <tr><td align="center" style="padding:24px 12px">
    <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #d9dee7;border-radius:10px">
      <tr><td style="background:#ffffff;padding:18px 24px 12px;border-bottom:3px solid #c8102e">
        {header_inner}
        <div style="font-family:Arial,sans-serif;font-size:11.5px;color:#6b7280;letter-spacing:.04em;margin-top:8px">INVOICE REQUEST · ACCOUNTS TEAM</div>
      </td></tr>
      <tr><td style="padding:20px 24px;font-family:Arial,sans-serif;color:#1a1a1a">
        <div style="font-size:15px">Hello {html.escape(greeting_name)},</div>
        <p style="font-size:14px;line-height:1.55;color:#333333;margin:12px 0 0">Please raise the <b>{pct}% {gate_word} invoice</b> for the project below and send it to the client.</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px">
          <tr>
            <td width="49%" style="background:#eef4fd;border:1px solid #c9dbfa;border-radius:8px;padding:12px 14px;text-align:center;font-family:Arial,sans-serif">
              <div style="font-size:11px;color:#5b7bb4;letter-spacing:.06em">PAYMENT GATE</div>
              <div style="font-size:24px;font-weight:bold;color:#12233f;margin:2px 0">{pct}%</div>
              <div style="font-size:12px;color:#5b7bb4">{gate_blurb}</div>
            </td>
            <td width="2%">&nbsp;</td>
            <td width="49%" style="background:#eefbf2;border:1px solid #bfe8cd;border-radius:8px;padding:12px 14px;text-align:center;font-family:Arial,sans-serif">
              <div style="font-size:11px;color:#4c8a5f;letter-spacing:.06em">INVOICE AMOUNT</div>
              <div style="font-size:24px;font-weight:bold;color:#14532d;margin:2px 0">{html.escape(amount_text)}</div>
              <div style="font-size:12px;color:#4c8a5f">{amount_sub}</div>
            </td>
          </tr>
        </table>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13.5px;margin-top:14px">
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666;width:150px">Project</td><td style="padding:8px 10px;border:1px solid #e2e6ee"><b>{html.escape(project.name)}</b></td></tr>
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666">Client</td><td style="padding:8px 10px;border:1px solid #e2e6ee">{html.escape(client_name)}</td></tr>
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666">Contract value</td><td style="padding:8px 10px;border:1px solid #e2e6ee">{html.escape(contract_text)}</td></tr>
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666">Requested by</td><td style="padding:8px 10px;border:1px solid #e2e6ee">{html.escape(requested_by)}</td></tr>
          <tr><td style="padding:8px 10px;border:1px solid #e2e6ee;background:#f8fafc;color:#666666">Request date</td><td style="padding:8px 10px;border:1px solid #e2e6ee">{date_text}</td></tr>
        </table>
        {note_html}
      </td></tr>
      <tr><td style="padding:2px 24px 20px;font-family:Arial,sans-serif">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td style="background:#2563eb;border-radius:7px"><a href="{html.escape(project_url)}" style="display:inline-block;padding:10px 20px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#ffffff;text-decoration:none">Open Project in ERP</a></td>
        </tr></table>
        <div style="font-size:12.5px;color:#666666;margin-top:10px">Once issued, please <b>reply to this email with the invoice number</b> for our records.</div>
        <div style="border-top:1px solid #e2e6ee;margin-top:18px;padding-top:12px;font-size:12px;color:#888888">Sent via OpenConstructionERP · Post-Award Pipeline · {stamp_text}</div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>
"""
    subject = f"[Action Required] Raise {pct}% Invoice — {project.name}"
    if amount is not None:
        subject += f" · {amount_text}"
    service = get_email_service()
    result = await service.send(
        EmailMessage(
            to=user.email,
            subject=subject,
            html_body=body,
            tags=["award_pipeline_invoice"],
            attachments=[logo] if logo is not None else [],
        )
    )
    if not result.ok:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Invoice email failed to send — check the mail settings and try again.",
        )
    milestone.inv_sent_at = _now()
    milestone.inv_sent_to = user.full_name or user.email
    # The milestone card's "Email sent to Accounts team..." confirmation
    # reads email_sent_at - with the auto-sends removed, this deliberate
    # popup send is the only writer, so the confirmation stays truthful.
    milestone.email_sent_at = _now()
    _sync_legacy_payment_columns(pipeline, milestone)
    await _log(
        session,
        pipeline,
        f"{pct}% invoice email sent to Accounting team",
        actor_id,
    )
    await session.flush()
    return await build_view(session, project, pipeline)


# ── Feedback stage ────────────────────────────────────────────────────


async def send_feedback(
    session: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: FeedbackSendIn,
) -> PipelineView:
    """Email the client asking for feedback — completes the pipeline.

    The Feedback stage unlocks 30 days after Delivered & Accepted.
    """
    from app.core.email.service import EmailMessage, get_email_service

    project = await _get_project(session, project_id)
    pipeline = await get_or_create_pipeline(session, project_id, actor_id)
    _require_stage(pipeline, "feedback", "send the feedback request")
    unlock = (
        pipeline.delivered_at + timedelta(days=30) if pipeline.delivered_at else None
    )
    if unlock is None or _now() < unlock:
        when = unlock.strftime("%d %b %Y") if unlock else "—"
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Feedback opens on {when} — 30 days after delivery.",
        )
    email = data.email.strip()
    if "@" not in email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter a valid client email.")
    subject = (data.subject or "").strip() or f"We value your feedback — {project.name}"
    message = (data.message or "").strip() or (
        f"Dear {await _client_name(session, project) or 'Client'},\n\n"
        f"Thank you for your business. The project {project.name} was delivered "
        "recently, and we would love to hear your feedback about our work. "
        "A short reply to this email is all it takes.\n\n"
        "Thank you!"
    )
    message_html = html.escape(message).replace("\n", "<br>")
    body = f"""
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#1a1a1a">
      <h2 style="margin:0 0 12px">{html.escape(subject)}</h2>
      <p>{message_html}</p>
    </div>
    """
    service = get_email_service()
    result = await service.send(
        EmailMessage(
            to=email,
            subject=subject,
            html_body=body,
            tags=["award_pipeline_feedback"],
        )
    )
    if not result.ok:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Feedback email failed to send — check the mail settings and try again.",
        )
    pipeline.feedback_sent_at = _now()
    pipeline.feedback_sent_by = actor_id
    pipeline.feedback_email = email
    pipeline.current_stage = "completed"
    await _log(session, pipeline, f"Feedback request sent to {email}", actor_id)
    await session.flush()
    return await build_view(session, project, pipeline)
