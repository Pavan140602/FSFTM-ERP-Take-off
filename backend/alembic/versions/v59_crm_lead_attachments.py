# OE-DELIVERY: 2026-10-15-lead-attachments-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""crm: LeadAttachment table for website bid-request file uploads.

``oe_crm_lead_attachment`` stores files attached to a sales lead
(fsftm.com/contact-us/ "File Upload", up to 5 files). Leads are
pre-project, so they cannot use the project-scoped Document store
(project_id is mandatory there) — lead attachments live under
``<data-dir>/uploads/lead-attachments/<lead_id>/`` instead.

Safe on a populated database: new table starts empty.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v59_crm_lead_attachments"
down_revision: Union[str, Sequence[str], None] = "v58_crm_lead_website_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oe_crm_lead_attachment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("stored_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column("uploaded_at", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["oe_crm_lead.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["oe_users_user.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_oe_crm_lead_attachment_lead_id",
        "oe_crm_lead_attachment",
        ["lead_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oe_crm_lead_attachment_lead_id",
        table_name="oe_crm_lead_attachment",
    )
    op.drop_table("oe_crm_lead_attachment")
