# OE-DELIVERY: 2026-10-21-award-pipeline-v5-fabstatus
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""projects: Post-Award Pipeline — fabrication status picklist column.

Adds ``fab_status`` ('started' | 'in_progress' | 'completed') to
``oe_projects_award_pipeline`` — the Fabrication card's Progress % field
was replaced by a status picklist.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v66_fab_status"
down_revision: Union[str, Sequence[str], None] = "v65_pipeline_stages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "oe_projects_award_pipeline"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    if "fab_status" not in existing:
        op.add_column(_TABLE, sa.Column("fab_status", sa.String(20), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    if "fab_status" in existing:
        op.drop_column(_TABLE, "fab_status")
