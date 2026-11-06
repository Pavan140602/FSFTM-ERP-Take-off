# OE-DELIVERY: 2026-10-21-pipeline-sends-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""projects: Post-Award Pipeline sends table.

``oe_projects_pipeline_send`` links a pipeline stage send (drafting /
shop_prep / shop_client) to the real File Transmittal created and sent
from inside the pipeline, so the panel can show the transmittal number
and the recipient's open/view tracking.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v64_pipeline_send"
down_revision: Union[str, Sequence[str], None] = "v63_award_pipeline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The PipelineActivity model maps an updated_at column (inherited
    # pattern from EstimationReview) but v63 created its table without
    # one — add it when missing so activity inserts cannot fail.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("oe_projects_pipeline_activity"):
        cols = {
            c["name"] for c in inspector.get_columns("oe_projects_pipeline_activity")
        }
        if "updated_at" not in cols:
            op.add_column(
                "oe_projects_pipeline_activity",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            )

    op.create_table(
        "oe_projects_pipeline_send",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(length=20), nullable=False),
        sa.Column("transmittal_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
        "ix_oe_projects_pipeline_send_pipeline_id",
        "oe_projects_pipeline_send",
        ["pipeline_id"],
    )
    op.create_index(
        "ix_oe_projects_pipeline_send_project_id",
        "oe_projects_pipeline_send",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oe_projects_pipeline_send_project_id",
        table_name="oe_projects_pipeline_send",
    )
    op.drop_index(
        "ix_oe_projects_pipeline_send_pipeline_id",
        table_name="oe_projects_pipeline_send",
    )
    op.drop_table("oe_projects_pipeline_send")
