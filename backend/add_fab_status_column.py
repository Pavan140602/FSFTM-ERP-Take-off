"""One-off: add the oe_projects_award_pipeline.fab_status column directly.

Same ritual as the v65 fix — this product never runs alembic upgrade,
and the boot heal can miss new columns on existing tables. Idempotent.

Run with the backend STOPPED, from the repo root:
    .\\.venv\\Scripts\\python.exe backend\\add_fab_status_column.py
Then start the backend again.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.core import embedded_pg

data_dir = Path.home() / ".openestimate"
if embedded_pg.is_requested():
    if not embedded_pg.boot(data_dir):
        raise SystemExit("Embedded PostgreSQL could not start — see the log above.")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    raise SystemExit("No DATABASE_URL after boot — cannot connect.")


async def _main() -> str | None:
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE oe_projects_award_pipeline "
                "ADD COLUMN IF NOT EXISTS fab_status VARCHAR(20)"
            )
        )
        result = await conn.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'oe_projects_award_pipeline' "
                "AND column_name = 'fab_status'"
            )
        )
        row = result.first()
    await engine.dispose()
    return row[0] if row else None


dtype = asyncio.run(_main())
print(f"fab_status: {dtype}")
if dtype != "character varying":
    raise SystemExit("fab_status column missing or wrong type!")
print("DONE — fab_status present. Now start the backend.")
