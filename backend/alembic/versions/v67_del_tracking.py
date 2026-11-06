# OE-DELIVERY: 2026-10-21-award-pipeline-v7-tracking
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""projects: Post-Award Pipeline — delivery tracking number column.

Adds ``del_tracking_number`` to ``oe_projects_award_pipeline`` — the
Delivery stage form gained a Tracking Number field next to Shipment Ref.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v67_del_tracking"
down_revision: Union[str, Sequence[str], None] = "v66_fab_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "oe_projects_award_pipeline"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    if "del_tracking_number" not in existing:
        op.add_column(
            _TABLE, sa.Column("del_tracking_number", sa.String(120), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    if "del_tracking_number" in existing:
        op.drop_column(_TABLE, "del_tracking_number")
