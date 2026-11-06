# OE-DELIVERY: 2026-10-15-estimation-review-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""projects: EstimationReview table for the internal estimation review workflow.

``oe_projects_estimation_review`` stores one review request per project
estimation. The estimator submits for review, picks Lead Estimator /
Coordinator / Manager as reviewers, and notifications go out. When the
Manager approves, the project moves to 'estimation_submitted'.

Safe on a populated database: new table starts empty.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "v60_estimation_review"
down_revision: Union[str, None] = "v59_crm_lead_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oe_projects_estimation_review",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("oe_projects_project.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("lead_estimator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("coordinator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("oe_projects_estimation_review")
