# OE-DELIVERY: 2026-10-27-receipt-edit (was 2026-10-27-payment-receipts)
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""Post-Award Pipeline — models + schemas.

When a project is awarded (won), it runs a pipeline of work stages
(Engineering / Drafting -> Shop Drawings -> Seal & Sign by EOR/AOR ->
Fabrication -> Delivery -> Feedback, which unlocks 30 days after
delivery) with payment milestones woven between them.

Design (agreed with the user, 2026-10-14 / go-ahead 2026-10-21,
payment schedule added 2026-10-27):

* Each payment milestone emails the Accounts team the project details
  only. Accounts invoices externally - the ERP creates NO Finance
  invoice. Marking a milestone "Received" only releases the next stage.
* The schedule is flexible per project: 3-5 milestones total (a fixed
  10% award milestone + 2-4 remainder milestones), remainder percents
  editable, and each remainder milestone positioned after any work
  stage via its anchor. All payment is collected BEFORE delivery - no
  milestone sits at or after the delivery stage.
* Partial receipts (OE-DELIVERY 2026-10-27): a milestone's target
  percent is fixed, but money rarely arrives in one payment, so any
  number of receipts can be recorded against it, in whatever amounts
  actually arrive - no pre-defined parts. Received = sum of receipts,
  balance = target - received. When received reaches the target the
  milestone completes exactly as "Mark Payment Received" does, and a
  completion email goes out automatically. Overpayment past the
  target carries forward to the next milestone in schedule order;
  past the final milestone it stays flagged as excess on that row.
  The panel shows the receipts UI only on non-award milestones; the
  award milestone keeps its single-step invoice + received flow.
* Drafting can be skipped by the Coordinator ("Skip drafting").
* Shop drawings are recorded as sent to the client; the Coordinator marks
  "Client Approved" when the client confirms - that unlocks the next
  payment milestone.
* Fabrication and Delivery are full records (vendor + dates + progress;
  shipment ref + carrier + ETA + a dispatched → in-transit → arrived
  tracker), not just checkboxes.

One ``AwardPipeline`` row per project holds the stage state; every action
appends a ``PipelineActivity`` row for the stage-activity timeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import GUID, Base

# Stage keys in pipeline order. "completed" is the terminal pseudo-stage.
STAGE_ORDER: list[str] = [
    "payment_10",
    "drafting",
    "shop_drawings",
    "seal_sign",
    "payment_60",
    "fabrication",
    "payment_30",
    "delivery",
    "feedback",
]
STAGE_LABELS: dict[str, str] = {
    "payment_10": "10% Payment",
    "drafting": "Engineering / Drafting",
    "shop_drawings": "Shop Drawings",
    "seal_sign": "Seal & Sign by EOR",
    "payment_60": "60% Payment",
    "fabrication": "Fabrication",
    "payment_30": "30% Payment",
    "delivery": "Delivery",
    "feedback": "Feedback",
}
# Payment gate percentage for the payment stages (legacy fixed gates;
# kept so older views and the legacy pay*_ columns keep working).
GATE_PCT: dict[str, int] = {"payment_10": 10, "payment_60": 60, "payment_30": 30}

# -- Flexible payment schedule (OE-DELIVERY 2026-10-27) --
# Work stages keep their fixed order. Payment milestones are woven
# between them by anchor: each remainder milestone appears right after
# its anchor's work stage. "before_delivery" sits after fabrication and
# before the delivery stage. There is deliberately NO anchor at or after
# delivery or feedback: this business collects 100% of payment BEFORE
# delivery, so a milestone due after delivery cannot exist.
WORK_STAGE_ORDER: list[str] = [
    "drafting",
    "shop_drawings",
    "seal_sign",
    "fabrication",
    "delivery",
    "feedback",
]
# anchor -> (display label, work stage the payment row follows)
MILESTONE_ANCHORS: dict[str, tuple[str, str]] = {
    "award": ("On award", "award"),
    "after_drafting": ("After Drafting", "drafting"),
    "after_shop_drawings": ("After Shop Drawings", "shop_drawings"),
    "after_seal_sign": ("After Seal & Sign", "seal_sign"),
    "after_fabrication": ("After Fabrication", "fabrication"),
    "before_delivery": ("Before Delivery", "fabrication"),
}
# Default schedule for new pipelines and for seeding legacy pipelines.
DEFAULT_MILESTONES: list[tuple[str, str, int]] = [
    ("award", "Advance", 10),
    ("after_seal_sign", "Progress", 60),
    ("after_fabrication", "Final", 30),
]
# Legacy gate columns track these anchors (award -> pay10, after-seal ->
# pay60, after-fabrication -> pay30) so older reads keep working.
LEGACY_ANCHOR_COLUMNS: dict[str, str] = {
    "award": "10",
    "after_seal_sign": "60",
    "after_fabrication": "30",
}
MIN_MILESTONES = 3
MAX_MILESTONES = 5


class AwardPipeline(Base):
    """Post-award pipeline state for one awarded project."""

    __tablename__ = "oe_projects_award_pipeline"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    current_stage: Mapped[str] = mapped_column(
        String(30), nullable=False, default="payment_10"
    )

    # ── Gate: 10% payment ─────────────────────────────────────────────
    pay10_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay10_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay10_received_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    pay10_inv_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay10_inv_sent_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Drafting ──────────────────────────────────────────────────────
    drafting_skipped: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    drafting_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    drafting_completed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    # ── Shop drawings ─────────────────────────────────────────────────
    shop_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shop_file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shop_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shop_sent_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    client_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    client_approved_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    # ── Seal & sign by EOR/AOR ────────────────────────────────────
    seal_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seal_completed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), nullable=True
    )

    # ── Gate: 60% payment ─────────────────────────────────────────────
    pay60_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay60_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay60_received_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    pay60_inv_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay60_inv_sent_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Fabrication ─────────────────────────────────────────────────
    fab_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fab_start_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fab_expected_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fab_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 'started' | 'in_progress' | 'completed' (UI picklist; progress kept
    # for the record, the picklist is what the user drives)
    fab_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fab_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fab_completed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    # ── Gate: 30% payment ─────────────────────────────────────────────
    pay30_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay30_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay30_received_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    pay30_inv_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pay30_inv_sent_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Delivery ──────────────────────────────────────────────────────
    del_shipment_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    del_tracking_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    del_carrier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    del_destination: Mapped[str | None] = mapped_column(String(500), nullable=True)
    del_eta: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # 'pending' | 'dispatched' | 'in_transit' | 'arrived'
    del_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    # ── Feedback (unlocks 30 days after delivery) ────────────────
    feedback_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    feedback_sent_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), nullable=True
    )
    feedback_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AwardPipeline project={self.project_id} stage={self.current_stage}>"


class PipelineActivity(Base):
    """One entry in a pipeline's stage-activity timeline."""

    __tablename__ = "oe_projects_pipeline_activity"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_award_pipeline.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PipelineActivity {self.id} {self.text[:40]!r}>"


class PipelineRevision(Base):
    """One review-round outcome on a pipeline stage.

    OE-DELIVERY 2026-10-26 (revision rounds + EOR reject loop): stages no
    longer complete exactly once. A revision request keeps the stage open
    and opens the next round; an EOR rejection returns the pipeline to
    Engineering / Drafting. Each outcome is one row so the panel can show
    the round history per stage. Outcomes:

      * ``revision_requested`` — reviewer asked for changes; the stage
        stays open and the next round begins.
      * ``approved`` — the stage's review passed (drafting completed /
        client approved); recorded for history, the stage advance itself
        is the approval.
      * ``eor_rejected`` — the EOR refused to seal at Seal & Sign.
      * ``eor_returned`` — the pipeline returned to Engineering /
        Drafting after an EOR rejection; opens a rework round there.

    The current round of a stage is 1 + the count of its
    ``revision_requested`` / ``eor_returned`` rows. New table, so
    ``create_all`` creates it on boot - no migration needed.
    """

    __tablename__ = "oe_projects_pipeline_revisions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_award_pipeline.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<PipelineRevision {self.stage} R{self.round_no} {self.outcome}>"


class PipelineSend(Base):
    """One real File Transmittal sent from inside the pipeline.

    Sends happen at four points:
      * ``drafting``    — drafting files sent from the Drafting stage
      * ``shop_prep``   — Step 1 of Shop Drawings: files sent FOR shop
                          drawing preparation (to the detailer)
      * ``shop_client`` — Step 2 of Shop Drawings: finished shop drawings
                          sent to the client for approval (recipient role
                          is forced to "Client")
      * ``fabrication`` — fabrication files sent to the vendor from the
                          Fabrication stage
    """

    __tablename__ = "oe_projects_pipeline_send"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_award_pipeline.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 'drafting' | 'shop_prep' | 'shop_client' | 'fabrication' | 'seal_sign'
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    transmittal_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PipelineSend {self.stage} transmittal={self.transmittal_id}>"


class PipelineMilestone(Base):
    """One payment milestone on a pipeline's flexible schedule.

    OE-DELIVERY 2026-10-27: the fixed 10/60/30 gates became a per-project
    schedule. Each pipeline has 3-5 rows: one fixed award milestone
    (anchor ``award``, 10%, first, unmovable) plus 2-4 remainder rows
    whose percent, label and anchor the user edits per project. ``key``
    is a short stable code (``m1``, ``m2``, ...) so the pipeline's
    ``current_stage`` can point at a milestone without exceeding its
    String(30) column; keys are never reused after a row is deleted.
    ``seq`` orders rows that share one anchor. A row with
    ``email_sent_at`` or ``received_at`` set is locked: its percent,
    label and anchor can no longer change, and it cannot be deleted.
    New table, so ``create_all`` creates it on boot - no migration
    needed, same as ``oe_projects_pipeline_revisions``.
    """

    __tablename__ = "oe_projects_pipeline_milestones"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_award_pipeline.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(20), nullable=False)
    anchor: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    percent: Mapped[int] = mapped_column(Integer, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    inv_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    inv_sent_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PipelineMilestone {self.key} {self.percent}% {self.anchor}>"


class PipelineReceipt(Base):
    """One partial payment recorded against a milestone.

    OE-DELIVERY 2026-10-27 (partial receipts): money is unpredictable,
    so receipts are recorded in whatever amounts actually arrive - no
    pre-defined parts. A milestone's received percent is the sum of its
    non-excess receipts; balance is target minus received. ``seq``
    orders receipts on one milestone (created_at ties are possible
    within one save). ``is_excess`` marks the leftover row kept on the
    final milestone when a payment overshoots the whole schedule - it
    is never silently dropped. New table, so ``create_all`` creates it
    on boot - no migration needed, same as the milestones table.
    """

    __tablename__ = "oe_projects_pipeline_receipts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    milestone_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_pipeline_milestones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    percent: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    is_excess: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PipelineReceipt {self.percent}% milestone={self.milestone_id}>"


# ── Schemas ──────────────────────────────────────────────────────────


class PipelineActivityOut(BaseModel):
    id: uuid.UUID
    text: str
    actor_name: str | None = None
    created_at: datetime


class PipelineRevisionOut(BaseModel):
    id: uuid.UUID
    stage: str
    round_no: int
    # revision_requested | approved | eor_rejected | eor_returned
    outcome: str
    comments: str | None = None
    actor_name: str | None = None
    created_at: datetime


class PipelineStageOut(BaseModel):
    key: str
    label: str
    # 'done' | 'current' | 'upcoming' | 'skipped'
    state: str
    completed_at: datetime | None = None
    # Payment stages only (OE-DELIVERY 2026-10-27): the milestone behind
    # this row, so the panel can show percent/label and drive the
    # invoice popup + "Mark received" without legacy gate keys.
    milestone_id: uuid.UUID | None = None
    percent: int | None = None
    milestone_label: str | None = None
    amount: float | None = None
    email_sent_at: datetime | None = None
    received_at: datetime | None = None
    inv_sent_at: datetime | None = None
    inv_sent_to: str | None = None


class PipelineReceiptOut(BaseModel):
    id: uuid.UUID
    milestone_id: uuid.UUID
    percent: float
    note: str | None = None
    is_excess: bool = False
    seq: int
    created_at: datetime


class PipelineReceiptIn(BaseModel):
    # Any positive percent - receipts arrive in unpredictable amounts,
    # so there are no pre-defined parts to pick from.
    percent: float = Field(gt=0, le=100)
    note: str | None = Field(default=None, max_length=500)


class PipelineReceiptUpdate(BaseModel):
    # Receipt edit (OE-DELIVERY 2026-10-27): percent and/or note.
    # Both optional - omitted fields keep their current value. A
    # provided note is stripped, and an empty note clears the stored
    # note (same convention as record). The server additionally
    # rejects edits on completed milestones, on excess rows, on
    # carried-forward rows, and on edits that would push the
    # milestone past its target.
    percent: float | None = Field(default=None, gt=0, le=100)
    note: str | None = Field(default=None, max_length=500)


class PipelineMilestoneOut(BaseModel):
    id: uuid.UUID
    key: str
    anchor: str
    anchor_label: str
    label: str
    percent: int
    seq: int
    amount: float | None = None
    email_sent_at: datetime | None = None
    received_at: datetime | None = None
    inv_sent_at: datetime | None = None
    inv_sent_to: str | None = None
    is_award: bool = False
    # Sent (email or received) rows are locked in the editor.
    is_sent: bool = False
    # Partial receipts (OE-DELIVERY 2026-10-27): received sums the
    # non-excess receipts, balance is target minus received, excess is
    # the overshoot kept on the final milestone. A milestone with any
    # receipt counts as sent for the editor lock.
    received_percent: float = 0.0
    balance_percent: float = 0.0
    excess_percent: float = 0.0
    receipts: list[PipelineReceiptOut] = Field(default_factory=list)


class PipelineMilestoneIn(BaseModel):
    # Existing row id, or null for a newly added milestone.
    id: uuid.UUID | None = None
    anchor: str = Field(min_length=1, max_length=30)
    label: str = Field(min_length=1, max_length=80)
    percent: int = Field(ge=1, le=99)


class SaveScheduleIn(BaseModel):
    """Full replacement schedule: the award row plus 2-4 remainder rows.

    The panel sends every row (existing ids preserved, new rows without
    an id); rows missing from the list are deleted. Server-side rules:
    3-5 rows total, exactly one award row at 10%, percents sum to 100,
    anchors from the allowed set, and sent rows unchanged.
    """

    milestones: list[PipelineMilestoneIn] = Field(min_length=3, max_length=5)


class PipelineView(BaseModel):
    project_id: uuid.UUID
    project_name: str
    client_name: str | None = None
    contract_value: str | None = None
    currency: str = ""
    gate_amounts: dict[str, float | None] = Field(default_factory=dict)
    current_stage: str
    progress_pct: int = 0
    stages: list[PipelineStageOut] = Field(default_factory=list)

    pay10_email_sent_at: datetime | None = None
    pay10_received_at: datetime | None = None
    pay10_inv_sent_at: datetime | None = None
    pay10_inv_sent_to: str | None = None

    drafting_skipped: bool = False
    drafting_completed_at: datetime | None = None

    shop_title: str | None = None
    shop_file_name: str | None = None
    shop_sent_at: datetime | None = None
    client_approved_at: datetime | None = None

    pay60_email_sent_at: datetime | None = None
    pay60_received_at: datetime | None = None
    pay60_inv_sent_at: datetime | None = None
    pay60_inv_sent_to: str | None = None

    seal_completed_at: datetime | None = None

    fab_vendor: str | None = None
    fab_start_date: str | None = None
    fab_expected_date: str | None = None
    fab_progress: int = 0
    fab_status: str | None = None
    fab_completed_at: datetime | None = None

    pay30_email_sent_at: datetime | None = None
    pay30_received_at: datetime | None = None
    pay30_inv_sent_at: datetime | None = None
    pay30_inv_sent_to: str | None = None

    del_shipment_ref: str | None = None
    del_tracking_number: str | None = None
    del_carrier: str | None = None
    del_destination: str | None = None
    del_eta: str | None = None
    del_status: str = "pending"
    delivered_at: datetime | None = None

    feedback_sent_at: datetime | None = None
    feedback_email: str | None = None
    feedback_unlock_at: datetime | None = None
    feedback_available: bool = False

    sends: list[PipelineSendOut] = Field(default_factory=list)
    activity: list[PipelineActivityOut] = Field(default_factory=list)

    # Review rounds (OE-DELIVERY 2026-10-26): chronological outcome rows
    # per stage, and the current round per reviewable stage (1-based;
    # a stage with no outcomes is on round 1).
    revisions: list[PipelineRevisionOut] = Field(default_factory=list)
    current_rounds: dict[str, int] = Field(default_factory=dict)

    # Flexible payment schedule (OE-DELIVERY 2026-10-27): the milestone
    # rows in schedule order (award first, then by anchor position and
    # seq). The dynamic stage list in ``stages`` already weaves these
    # rows between the work stages.
    milestones: list[PipelineMilestoneOut] = Field(default_factory=list)


class PipelineSendOut(BaseModel):
    id: uuid.UUID
    stage: str
    transmittal_id: uuid.UUID
    transmittal_number: str | None = None
    subject: str | None = None
    recipient_email: str | None = None
    recipient_name: str | None = None
    recipient_role: str | None = None
    recipient_count: int = 1
    file_names: list[str] = Field(default_factory=list)
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    viewed_at: datetime | None = None
    view_count: int = 0
    acknowledged_at: datetime | None = None


class PipelineSendFile(BaseModel):
    file_id: str = Field(min_length=1, max_length=64)
    file_kind: str = Field(default="document", max_length=32)
    name: str = Field(min_length=1, max_length=512)


class PipelineRecipientIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str | None = Field(default=None, max_length=128)
    role: str | None = Field(default=None, max_length=32)


class PipelineSendIn(BaseModel):
    # 'drafting' | 'shop_prep' | 'shop_client' | 'fabrication' | 'seal_sign'
    stage: str = Field(min_length=1, max_length=20)
    # Single-recipient form (recipient_email) OR multi-recipient form
    # (recipients list — everyone on ONE transmittal; the panel groups
    # by role and calls once per role, so each group gets its own
    # transmittal with its own subject/message).
    recipient_email: str | None = Field(default=None, max_length=255)
    recipient_name: str | None = Field(default=None, max_length=128)
    recipient_role: str | None = Field(default=None, max_length=32)
    recipients: list[PipelineRecipientIn] | None = Field(default=None, max_length=25)
    subject: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=4000)
    files: list[PipelineSendFile] = Field(min_length=1, max_length=50)


class InvoiceEmailIn(BaseModel):
    """Ask an Accounts user (popup selection) to invoice the client.

    OE-DELIVERY 2026-10-27: the milestone drives the email - its percent
    and label fill the popup title, the subject and the body. ``gate``
    is the legacy form (10/60/30): when no milestone_id is given it
    resolves to the milestone on the matching legacy anchor.
    """

    gate: int | None = Field(
        default=None, description="Legacy payment gate percentage: 10, 60 or 30"
    )
    milestone_id: uuid.UUID | None = None
    user_id: uuid.UUID
    message: str | None = Field(default=None, max_length=4000)


class FeedbackSendIn(BaseModel):
    """Feedback-request email to the client (Feedback stage)."""

    email: str = Field(min_length=3, max_length=255)
    subject: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=4000)


class AccountsUserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str


class PaymentReceivedIn(BaseModel):
    """Mark one payment milestone received - releases the next stage.

    OE-DELIVERY 2026-10-27: ``milestone_id`` is the current form;
    ``gate`` is the legacy form (10/60/30) resolving to the milestone
    on the matching legacy anchor.
    """

    gate: int | None = Field(
        default=None, description="Legacy payment gate percentage: 10, 60 or 30"
    )
    milestone_id: uuid.UUID | None = None


class ShopSentIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    file_name: str | None = Field(default=None, max_length=500)


class FabricationIn(BaseModel):
    status: str | None = Field(
        default=None, description="started | in_progress | completed"
    )
    vendor: str | None = Field(default=None, max_length=255)
    start_date: str | None = Field(default=None, max_length=40)
    expected_date: str | None = Field(default=None, max_length=40)
    progress: int | None = Field(default=None, ge=0, le=100)


class RevisionIn(BaseModel):
    """Request another review round on the current stage (drafting /
    shop_drawings). The stage stays open; the next round begins."""

    comments: str = Field(min_length=1, max_length=2000)


class RejectSealIn(BaseModel):
    """EOR refuses to seal: the pipeline returns to Engineering /
    Drafting. Comments are required — they travel back as the rework
    brief."""

    comments: str = Field(min_length=1, max_length=2000)


class DeliveryIn(BaseModel):
    shipment_ref: str | None = Field(default=None, max_length=120)
    tracking_number: str | None = Field(default=None, max_length=120)
    carrier: str | None = Field(default=None, max_length=255)
    destination: str | None = Field(default=None, max_length=500)
    eta: str | None = Field(default=None, max_length=40)
    status: str | None = Field(
        default=None, description="pending | dispatched | in_transit | arrived"
    )
