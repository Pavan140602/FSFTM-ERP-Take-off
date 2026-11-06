# OE-DELIVERY: 2026-10-21-award-pipeline-v4-stages
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""projects: Post-Award Pipeline — Seal & Sign + Feedback stages, invoice emails.

Adds to ``oe_projects_award_pipeline``:
  * per-gate invoice-email stamps (pay10/pay60/pay30 ``inv_sent_at`` +
    ``inv_sent_to``) for the "Send {gate}% Invoice to Client" popup;
  * ``seal_completed_at`` / ``seal_completed_by`` for the new
    Seal & Sign by EOR/AOR stage (no new table — sends reuse
    ``oe_projects_pipeline_send`` with stage 'seal_sign');
  * ``feedback_sent_at`` / ``feedback_sent_by`` / ``feedback_email``
    for the Feedback stage (unlocks 30 days after delivery).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v65_pipeline_stages"
down_revision: Union[str, Sequence[str], None] = "v64_pipeline_send"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "oe_projects_award_pipeline"


def _add_missing(columns: list[tuple[str, sa.Column]]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    for name, column in columns:
        if name not in existing:
            op.add_column(_TABLE, column)


def upgrade() -> None:
    dt = lambda: sa.DateTime(timezone=True)  # noqa: E731
    _add_missing(
        [
            ("pay10_inv_sent_at", sa.Column("pay10_inv_sent_at", dt(), nullable=True)),
            ("pay10_inv_sent_to", sa.Column("pay10_inv_sent_to", sa.String(255), nullable=True)),
            ("pay60_inv_sent_at", sa.Column("pay60_inv_sent_at", dt(), nullable=True)),
            ("pay60_inv_sent_to", sa.Column("pay60_inv_sent_to", sa.String(255), nullable=True)),
            ("pay30_inv_sent_at", sa.Column("pay30_inv_sent_at", dt(), nullable=True)),
            ("pay30_inv_sent_to", sa.Column("pay30_inv_sent_to", sa.String(255), nullable=True)),
            ("seal_completed_at", sa.Column("seal_completed_at", dt(), nullable=True)),
            ("seal_completed_by", sa.Column("seal_completed_by", sa.Uuid(), nullable=True)),
            ("feedback_sent_at", sa.Column("feedback_sent_at", dt(), nullable=True)),
            ("feedback_sent_by", sa.Column("feedback_sent_by", sa.Uuid(), nullable=True)),
            ("feedback_email", sa.Column("feedback_email", sa.String(255), nullable=True)),
        ]
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    existing = {c["name"] for c in inspector.get_columns(_TABLE)}
    for name in (
        "feedback_email",
        "feedback_sent_by",
        "feedback_sent_at",
        "seal_completed_by",
        "seal_completed_at",
        "pay30_inv_sent_to",
        "pay30_inv_sent_at",
        "pay60_inv_sent_to",
        "pay60_inv_sent_at",
        "pay10_inv_sent_to",
        "pay10_inv_sent_at",
    ):
        if name in existing:
            op.drop_column(_TABLE, name)
