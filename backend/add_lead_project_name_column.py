"""One-off fix: add the lead project_name column directly.

Why: this product never runs `alembic upgrade` - the schema moves via
create_all (which never alters existing tables) plus boot-time heal, and
the CRM module has no heal for leads, so a new Lead.project_name column
would silently never land on the live database. This script boots the
same embedded PostgreSQL the CLI uses and adds the column idempotently.

OE-DELIVERY: 2026-10-27-lead-project-name

Run with the backend STOPPED, from the repo root, with the venv python.
Place this file in backend/ first (it imports app.core), then run:
    .\\.venv\\Scripts\\python.exe backend\\add_lead_project_name_column.py
Then start the backend again:
    openconstructionerp serve --port 8000
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core import embedded_pg

data_dir = Path.home() / ".openestimate"
if embedded_pg.is_requested():
    if not embedded_pg.boot(data_dir):
        raise SystemExit("Embedded PostgreSQL could not start - see the log above.")

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# The app runs on the async (asyncpg) driver; the sync psycopg2 driver is
# not installed on this machine, so use DATABASE_URL with an async engine.
db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    raise SystemExit("No DATABASE_URL after boot - cannot connect.")

COLUMNS: list[tuple[str, str]] = [
    ("project_name", "VARCHAR(255)"),
]


async def _main() -> list[str]:
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        for name, ddl in COLUMNS:
            await conn.execute(
                text(
                    "ALTER TABLE oe_crm_lead "
                    f"ADD COLUMN IF NOT EXISTS {name} {ddl}"
                )
            )
            print(f"column ok: {name}")
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'oe_crm_lead' "
                "ORDER BY column_name"
            )
        )
        rows = list(result.scalars().all())
    await engine.dispose()
    return rows


rows = asyncio.run(_main())
print("\nTable now has", len(rows), "columns.")
missing = [name for name, _ in COLUMNS if name not in rows]
if missing:
    raise SystemExit(f"STILL MISSING: {missing}")
print("DONE - project_name column present. Now run the code patch, then start the backend.")
