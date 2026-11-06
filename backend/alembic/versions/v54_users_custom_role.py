# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""users: admin-defined custom roles.

Creates one table and touches no existing one:

    oe_users_custom_role - one row per admin-created role category
    (e.g. "Senior Estimator"). A user carries the role through the free-form
    ``oe_users_user.role`` column as the slug (``custom_senior_estimator``),
    so no change to the users table is needed.

Columns:

    slug            - ``custom_``-prefixed, unique; the value stored on
                      ``User.role`` and the key the permission engine's
                      in-memory cache is keyed by.
    name            - human label shown in the Users page dropdowns.
    description     - optional admin note.
    base_role       - one of the canonical four (default ``editor``); sets
                      the rank and the starting permission list.
    granted_modules - JSON list of module keys; permissions whose module is
                      not listed are removed from the base role's list.
    is_active       - soft switch; inactive rows are invisible to the UI and
                      are not pushed into the permission cache.
    created_by      - UUID of the creating admin, no FK (a later GDPR
                      erasure of that admin must never be blocked by this).

Safe on a populated database: one CREATE TABLE and one unique CREATE INDEX
on a table that did not exist, so no existing row is read, rewritten or
locked.

Inspector-guarded, so a fresh install whose tables env.py already created
through ``Base.metadata.create_all`` hits an idempotent no-op.

Revision ID: v54_users_custom_role
Revises: v53_schedule_activity_client_visible
Create Date: 2026-10-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v54_users_custom_role"
down_revision: Union[str, Sequence[str], None] = "v53_schedule_activity_client_visible"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "oe_users_custom_role"

# ``GUID`` renders as String(36) on every dialect and the ORM's timestamps are
# TIMESTAMP WITH TIME ZONE. Neither is a native ``uuid`` column.
_GUID = sa.String(36)
_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    """Create the custom-role table (idempotent)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE in inspector.get_table_names():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", _GUID, primary_key=True, nullable=False),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.func.now()),
        # The value stored on User.role; always custom_-prefixed.
        sa.Column("slug", sa.String(60), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_role", sa.String(20), nullable=False, server_default="editor"),
        sa.Column("granted_modules", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        # No FK: the creator may later be GDPR-erased, and a dangling creator
        # id must never block that.
        sa.Column("created_by", _GUID, nullable=True),
    )
    op.create_index(f"ix_{_TABLE}_slug", _TABLE, ["slug"], unique=True)


def downgrade() -> None:
    """Drop the custom-role table again."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return
    op.drop_index(f"ix_{_TABLE}_slug", table_name=_TABLE)
    op.drop_table(_TABLE)
