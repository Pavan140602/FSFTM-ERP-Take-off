"""One-off fix: add the v65 Post-Award Pipeline columns directly.

Why: this product never runs `alembic upgrade` — the schema moves via
create_all (which never alters existing tables) plus the boot-time heal,
and the heal missed these columns, so every pipeline read failed with
UndefinedColumnError. This script boots the same embedded PostgreSQL
the CLI uses and adds the columns idempotently.

Run with the backend STOPPED, from the repo root, venv active:
    python backend\\fix_v65_columns.py
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
        raise SystemExit("Embedded PostgreSQL could not start — see the log above.")

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# The app runs on the async (asyncpg) driver; the sync psycopg2 driver is
# not installed on this machine, so use DATABASE_URL with an async engine.
db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    raise SystemExit("No DATABASE_URL after boot — cannot connect.")

COLUMNS: list[tuple[str, str]] = [
    ("pay10_inv_sent_at", "TIMESTAMPTZ"),
    ("pay10_inv_sent_to", "VARCHAR(255)"),
    ("pay60_inv_sent_at", "TIMESTAMPTZ"),
    ("pay60_inv_sent_to", "VARCHAR(255)"),
    ("pay30_inv_sent_at", "TIMESTAMPTZ"),
    ("pay30_inv_sent_to", "VARCHAR(255)"),
    ("seal_completed_at", "TIMESTAMPTZ"),
    ("seal_completed_by", "UUID"),
    ("feedback_sent_at", "TIMESTAMPTZ"),
    ("feedback_sent_by", "UUID"),
    ("feedback_email", "VARCHAR(255)"),
]

async def _main() -> list[str]:
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        for name, ddl in COLUMNS:
            await conn.execute(
                text(
                    "ALTER TABLE oe_projects_award_pipeline "
                    f"ADD COLUMN IF NOT EXISTS {name} {ddl}"
                )
            )
            print(f"column ok: {name}")
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'oe_projects_award_pipeline' "
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
print("DONE — all v65 columns present. Now start the backend.")
