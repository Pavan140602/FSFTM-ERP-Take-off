# OE-DELIVERY: 2026-10-21-award-pipeline-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""projects: Post-Award Pipeline tables.

``oe_projects_award_pipeline`` holds the 7-stage post-award state for one
awarded project (10% payment → drafting → shop drawings → 60% payment →
fabrication → 30% payment → delivery). ``oe_projects_pipeline_activity``
is its stage-activity timeline.

Safe on a populated database: new tables start empty; pipelines are
created lazily the first time an awarded project is opened.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v63_award_pipeline"
down_revision: Union[str, Sequence[str], None] = "v62_crm_opportunity_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oe_projects_award_pipeline",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("current_stage", sa.String(length=30), nullable=False, server_default="payment_10"),
        sa.Column("pay10_email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pay10_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pay10_received_by", sa.Uuid(), nullable=True),
        sa.Column("drafting_skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("drafting_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("drafting_completed_by", sa.Uuid(), nullable=True),
        sa.Column("shop_title", sa.String(length=500), nullable=True),
        sa.Column("shop_file_name", sa.String(length=500), nullable=True),
        sa.Column("shop_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shop_sent_by", sa.Uuid(), nullable=True),
        sa.Column("client_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_approved_by", sa.Uuid(), nullable=True),
        sa.Column("pay60_email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pay60_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pay60_received_by", sa.Uuid(), nullable=True),
        sa.Column("fab_vendor", sa.String(length=255), nullable=True),
        sa.Column("fab_start_date", sa.String(length=40), nullable=True),
        sa.Column("fab_expected_date", sa.String(length=40), nullable=True),
        sa.Column("fab_progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fab_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fab_completed_by", sa.Uuid(), nullable=True),
        sa.Column("pay30_email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pay30_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pay30_received_by", sa.Uuid(), nullable=True),
        sa.Column("del_shipment_ref", sa.String(length=120), nullable=True),
        sa.Column("del_carrier", sa.String(length=255), nullable=True),
        sa.Column("del_destination", sa.String(length=500), nullable=True),
        sa.Column("del_eta", sa.String(length=40), nullable=True),
        sa.Column("del_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["oe_projects_project.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_oe_projects_award_pipeline_project"),
    )
    op.create_index(
        "ix_oe_projects_award_pipeline_project_id",
        "oe_projects_award_pipeline",
        ["project_id"],
    )
    op.create_table(
        "oe_projects_pipeline_activity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["oe_projects_award_pipeline.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["oe_projects_project.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_oe_projects_pipeline_activity_pipeline_id",
        "oe_projects_pipeline_activity",
        ["pipeline_id"],
    )
    op.create_index(
        "ix_oe_projects_pipeline_activity_project_id",
        "oe_projects_pipeline_activity",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oe_projects_pipeline_activity_project_id",
        table_name="oe_projects_pipeline_activity",
    )
    op.drop_index(
        "ix_oe_projects_pipeline_activity_pipeline_id",
        table_name="oe_projects_pipeline_activity",
    )
    op.drop_table("oe_projects_pipeline_activity")
    op.drop_index(
        "ix_oe_projects_award_pipeline_project_id",
        table_name="oe_projects_award_pipeline",
    )
    op.drop_table("oe_projects_award_pipeline")
