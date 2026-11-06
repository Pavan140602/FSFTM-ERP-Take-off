# OE-DELIVERY: 2026-10-15-lead-website-fields-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""crm: website bid-request form fields on Lead.

Adds ``category`` / ``bid_requested_for`` / ``message`` to ``oe_crm_lead``
so the fsftm.com/contact-us/ bid-request form fields ("Select Category"
picklist, "Bid requested for" picklist, "Message" textarea) are stored on
the Lead — both for manual New-Lead entry and for the webhook-leads
mapping (the webhook allowlist is extended in the same delivery).

Safe on a populated database: all three columns are nullable, existing
rows stay NULL.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v58_crm_lead_website_fields"
down_revision: Union[str, Sequence[str], None] = "v57_file_transmittals_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oe_crm_lead",
        sa.Column("category", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "oe_crm_lead",
        sa.Column("bid_requested_for", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "oe_crm_lead",
        sa.Column("message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oe_crm_lead", "message")
    op.drop_column("oe_crm_lead", "bid_requested_for")
    op.drop_column("oe_crm_lead", "category")
