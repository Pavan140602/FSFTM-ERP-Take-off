"""
Backfill: copy lead attachments into their converted opportunities.

Run AFTER applying service_bid_awarded_v2_lead_opp_carry.py + backend restart.
This handles leads that were converted BEFORE the carry-over fix.

Usage (from backend/ dir with .venv active):
    python backfill_lead_opp_attachments.py

It finds every converted lead that has file attachments, and copies any
missing files into its opportunity's attachment store
(<data-dir>/uploads/opportunity-attachments/<opp_id>/).
Safe to re-run: skips files already present (matched by file_name).
"""
import asyncio
import os
import shutil
import sys
import uuid
from pathlib import Path

# Ensure the backend/ dir (this script's location) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Boot embedded PostgreSQL (same as CLI) so DATABASE_URL is set.
# If the server is already running, this detects the live cluster.
from app.core.storage import resolve_data_dir
from app.core import embedded_pg
if embedded_pg.is_requested():
    embedded_pg.boot(resolve_data_dir())

from sqlalchemy import select

from app.database import async_session_factory
from app.modules.crm.models import Lead, LeadAttachment, Opportunity, OpportunityAttachment


async def main() -> None:
    async with async_session_factory() as session:
        # Converted leads that have attachments
        leads = (
            await session.execute(
                select(Lead).where(Lead.converted_opportunity_id.is_not(None))
            )
        ).scalars().all()

        total_copied = 0
        for lead in leads:
            opp_id = lead.converted_opportunity_id
            atts = (
                await session.execute(
                    select(LeadAttachment).where(LeadAttachment.lead_id == lead.id)
                )
            ).scalars().all()
            if not atts:
                continue

            existing = (
                await session.execute(
                    select(OpportunityAttachment.file_name).where(
                        OpportunityAttachment.opportunity_id == opp_id
                    )
                )
            ).scalars().all()
            existing_names = set(existing)

            opp_dir = (
                Path(resolve_data_dir()) / "uploads" / "opportunity-attachments" / str(opp_id)
            )
            opp_dir.mkdir(parents=True, exist_ok=True)

            for att in atts:
                if att.file_name in existing_names:
                    continue
                if not att.stored_path or not os.path.isfile(att.stored_path):
                    print(f"  SKIP missing on disk: {att.file_name}")
                    continue
                dest = opp_dir / f"{uuid.uuid4().hex[:12]}_{att.file_name}"
                shutil.copy2(att.stored_path, dest)
                session.add(
                    OpportunityAttachment(
                        opportunity_id=opp_id,
                        file_name=att.file_name,
                        stored_path=str(dest),
                        size_bytes=att.size_bytes or 0,
                        mime_type=att.mime_type or "",
                        uploaded_by=str(att.uploaded_by) if att.uploaded_by else None,
                    )
                )
                total_copied += 1
                print(f"  copied: {att.file_name} -> opp {opp_id}")

        await session.commit()
        print(f"\nDone. {total_copied} file(s) backfilled.")


if __name__ == "__main__":
    asyncio.run(main())
