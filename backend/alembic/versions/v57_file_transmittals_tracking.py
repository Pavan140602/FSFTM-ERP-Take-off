# OE-DELIVERY: 2026-10-14-transmittal-tracking-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""file_transmittals: delivery tracking (email open / page view / file view).

Adds ``opened_at`` / ``viewed_at`` / ``view_count`` to
``oe_file_transmittal_recipient`` and a new
``oe_file_transmittal_file_view`` table (one row per recipient+file,
upserted on every view).

- opened_at: first email-open, stamped by the tracking-pixel endpoint.
- viewed_at: first public-page view, stamped by the public view endpoint.
- file_view rows: which file the recipient opened, when, and how often.

Safe on a populated database: new columns are nullable / default 0,
new table starts empty.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v57_file_transmittals_tracking"
down_revision: Union[str, Sequence[str], None] = "v56_users_smtp_automated_optin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oe_file_transmittal_recipient",
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "oe_file_transmittal_recipient",
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "oe_file_transmittal_recipient",
        sa.Column(
            "view_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_table(
        "oe_file_transmittal_file_view",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transmittal_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("file_kind", sa.String(length=32), nullable=False),
        sa.Column("file_id", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["transmittal_id"],
            ["oe_file_transmittal.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["oe_file_transmittal_recipient.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recipient_id",
            "file_kind",
            "file_id",
            name="uq_oe_file_transmittal_file_view_recipient_file",
        ),
    )
    op.create_index(
        "ix_oe_file_transmittal_file_view_transmittal_id",
        "oe_file_transmittal_file_view",
        ["transmittal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oe_file_transmittal_file_view_transmittal_id",
        table_name="oe_file_transmittal_file_view",
    )
    op.drop_table("oe_file_transmittal_file_view")
    op.drop_column("oe_file_transmittal_recipient", "view_count")
    op.drop_column("oe_file_transmittal_recipient", "viewed_at")
    op.drop_column("oe_file_transmittal_recipient", "opened_at")
