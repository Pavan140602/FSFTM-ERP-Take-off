# OE-DELIVERY: 2026-10-16-role-module-config-v1
"""v61: per-role module visibility configuration.

Admin configures which modules each role (canonical + custom) can see.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "v61_role_module_config"
down_revision: Union[str, None] = "v60_estimation_review"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oe_role_module_config",
        sa.Column("role_slug", sa.String(60), primary_key=True),
        sa.Column(
            "granted_modules",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("oe_role_module_config")
