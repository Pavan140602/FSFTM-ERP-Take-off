# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""users: per-user SMTP settings (individual sender).

Adds nullable SMTP columns to ``oe_users_user`` so each user can configure
their own mail provider. Task-assignment emails then send through the
assigner's SMTP with their own From address, instead of the system SMTP.

Columns (all nullable except the two booleans):

    smtp_host         - e.g. smtp.zoho.com / smtp.gmail.com
    smtp_port         - 587 (STARTTLS) or 465 (implicit TLS)
    smtp_username     - SMTP login
    smtp_password_enc - Fernet-encrypted (app.core.crypto)
    smtp_from         - From address shown to recipients
    smtp_tls          - STARTTLS for port 587 (default True)
    smtp_enabled      - master switch; False = fall back to system SMTP

Safe on a populated database: only ADD COLUMN with NULL/defaults, no
existing data touched.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v55_users_smtp_settings"
down_revision: Union[str, Sequence[str], None] = "v54_users_custom_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("oe_users_user", sa.Column("smtp_host", sa.String(255), nullable=True))
    op.add_column("oe_users_user", sa.Column("smtp_port", sa.Integer(), nullable=True))
    op.add_column("oe_users_user", sa.Column("smtp_username", sa.String(255), nullable=True))
    op.add_column(
        "oe_users_user", sa.Column("smtp_password_enc", sa.String(1024), nullable=True)
    )
    op.add_column("oe_users_user", sa.Column("smtp_from", sa.String(255), nullable=True))
    op.add_column(
        "oe_users_user",
        sa.Column("smtp_tls", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "oe_users_user",
        sa.Column("smtp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    for col in (
        "smtp_enabled",
        "smtp_tls",
        "smtp_from",
        "smtp_password_enc",
        "smtp_username",
        "smtp_port",
        "smtp_host",
    ):
        op.drop_column("oe_users_user", col)
