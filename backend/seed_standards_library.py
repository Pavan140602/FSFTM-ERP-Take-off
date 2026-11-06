"""Seed the Standards Library tables from the verified data package.

OE-DELIVERY: 2026-10-29-standards-library-v1

Creates the three standards tables (if missing) and loads:
    aisc_sections.json   - 2,299 AISC shapes (AISC Shapes Database v16.0)
    ssma_sections.json   - 481 SSMA stud/track property rows (SSMA Technical Guide)
    divisions.json       - MasterFormat divisions + FSFTM sections

Idempotent: divisions are rebuilt, sections are upserted by
(source, designation), so re-running only refreshes values.

Run with the backend STOPPED, from the repo root, with the venv python.
Place this script and the three JSON files in backend/ first, plus the
standards_library module under backend/app/modules/standards_library/.
Then start the backend:
    openconstructionerp serve --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from app.core import embedded_pg

data_dir = Path.home() / ".openestimate"
if embedded_pg.is_requested():
    if not embedded_pg.boot(data_dir):
        raise SystemExit("Embedded PostgreSQL could not start - see the log above.")

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.modules.standards_library.models import (
    StandardsDivision,
    StandardsDocument,
    StandardsSection,
)
from app.modules.standards_library.service import (
    candidate_keys,
    section_values_from_seed,
)

HERE = Path(__file__).resolve().parent

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    raise SystemExit("No DATABASE_URL after boot - cannot connect.")


def _load(name: str):
    with open(HERE / name, encoding="utf-8") as f:
        return json.load(f)


async def _main() -> None:
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c,
                tables=[
                    StandardsSection.__table__,
                    StandardsDivision.__table__,
                    StandardsDocument.__table__,
                ],
            )
        )
    print("tables ok: oe_standards_section, oe_standards_division, oe_standards_document")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        # Divisions: small reference table - rebuild it wholesale.
        await session.execute(delete(StandardsDivision))
        div_data = _load("divisions.json")
        for d in div_data["divisions"]:
            session.add(StandardsDivision(code=d["code"], title=d["title"], kind="division"))
        for s in div_data["sections"]:
            session.add(
                StandardsDivision(
                    code=s["code"], title=s["title"], kind="section", parent_code=s["division"]
                )
            )
        await session.commit()
        print(f"divisions loaded: {len(div_data['divisions'])} + {len(div_data['sections'])} sections")

        # Sections: upsert by (source, designation).
        # Sections: drop stale rows from earlier seed versions first
        # (e.g. designations that carried a footnote digit), then upsert.
        incoming: dict[str, list[dict]] = {}
        for name in ("aisc_sections.json", "ssma_sections.json"):
            for row in _load(name):
                incoming.setdefault(row["source"], []).append(row)
        for source, rows_in in incoming.items():
            keep = [r["designation"] for r in rows_in]
            stale = await session.execute(
                delete(StandardsSection).where(
                    StandardsSection.source == source,
                    ~StandardsSection.designation.in_(keep),
                )
            )
            if stale.rowcount:
                print(f"removed {stale.rowcount} stale {source} rows from an earlier seed")
        await session.commit()

        existing = {
            (r.source, r.designation): r
            for r in (await session.execute(select(StandardsSection))).scalars().all()
        }
        inserted = updated = 0
        for rows_in in incoming.values():
            for row in rows_in:
                values = section_values_from_seed(row)
                key = (values["source"], values["designation"])
                current = existing.get(key)
                if current is None:
                    session.add(StandardsSection(**values))
                    inserted += 1
                else:
                    for field, value in values.items():
                        setattr(current, field, value)
                    updated += 1
        await session.commit()
        print(f"sections: {inserted} inserted, {updated} updated")

        # Verification lookups (manual-label and EDI forms).
        for probe in ("W10X26", "HSS6X2X1/8", "HSS6X2X.125", "hss 6x2x1/8", "600S162-54"):
            keys = candidate_keys(probe)
            stmt = select(StandardsSection).where(
                StandardsSection.lookup_key.in_(keys) | StandardsSection.edi_key.in_(keys)
            )
            hit = (await session.execute(stmt)).scalars().first()
            if hit is None:
                print(f"  lookup {probe!r}: NO MATCH")
            else:
                print(f"  lookup {probe!r}: {hit.designation} = {hit.weight_lb_ft} lb/ft")
    await engine.dispose()
    print("DONE - Standards Library seeded. Now start the backend.")


if __name__ == "__main__":
    asyncio.run(_main())
