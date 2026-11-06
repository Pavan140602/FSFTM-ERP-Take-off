# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""users: opt-in flag for per-user SMTP on automated emails.

Adds ``smtp_use_for_automated`` to ``oe_users_user``. When True (and the
user's SMTP is configured + enabled), automated emails (task assigned,
etc.) go through the user's own provider — their Sent box will contain
them. When False (default), the system SMTP sends with
"Name via FSFTM ERP" as From and the user's address as Reply-To, keeping
the user's Sent box clean (Zoho-CRM-notifications style).

Safe on a populated database: single ADD COLUMN with default False.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v56_users_smtp_automated_optin"
down_revision: Union[str, Sequence[str], None] = "v55_users_smtp_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oe_users_user",
        sa.Column(
            "smtp_use_for_automated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("oe_users_user", "smtp_use_for_automated")
