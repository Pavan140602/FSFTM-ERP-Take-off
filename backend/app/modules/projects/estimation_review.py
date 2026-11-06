# OE-DELIVERY: 2026-10-15-estimation-review-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""Estimation internal review workflow.

When a project is in the Estimating stage, the estimator (or manager) can
submit it for internal review. They pick three reviewers — Lead Estimator,
Coordinator, Manager — and notifications go to each. When the Manager
approves, the project automatically moves to 'estimation_submitted'
(Estimation Submitted tab).

Only the Manager's approval triggers the move; the other reviewers are
notified for visibility/input.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import GUID, Base


class EstimationReview(Base):
    """One internal review request for a project's estimation."""

    __tablename__ = "oe_projects_estimation_review"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("oe_projects_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    # 'pending' | 'approved' | 'rejected'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    lead_estimator_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    coordinator_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    manager_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
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
        return f"<EstimationReview {self.id} project={self.project_id} status={self.status}>"


# ── Schemas ──────────────────────────────────────────────────────────


class EstimationReviewSubmit(BaseModel):
    """Submit a project for internal review."""

    lead_estimator_id: uuid.UUID | None = Field(default=None)
    coordinator_id: uuid.UUID | None = Field(default=None)
    manager_id: uuid.UUID | None = Field(default=None)
    note: str | None = Field(default=None, max_length=2000)


class EstimationReviewResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    submitted_by: uuid.UUID
    status: str
    lead_estimator_id: uuid.UUID | None
    coordinator_id: uuid.UUID | None
    manager_id: uuid.UUID | None
    manager_approved_at: datetime | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
