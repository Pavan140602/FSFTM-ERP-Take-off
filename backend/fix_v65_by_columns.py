"""One-off fix #2: correct the two *_by column types from the v65 fix.

add_pipeline_columns.py added seal_completed_by / feedback_sent_by as
UUID, but this app's GUID type binds as VARCHAR and every other *_by
column in oe_projects_award_pipeline is VARCHAR — inserts failed with
DatatypeMismatchError. This converts both columns to VARCHAR(36).
They are all NULL (never written), so the type change is safe.

Run with the backend STOPPED, from the repo root:
    .\\.venv\\Scripts\\python.exe backend\\fix_v65_by_columns.py
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

COLUMNS = ["seal_completed_by", "feedback_sent_by"]


async def _main() -> dict[str, str]:
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        for name in COLUMNS:
            await conn.execute(
                text(
                    "ALTER TABLE oe_projects_award_pipeline "
                    f"ALTER COLUMN {name} TYPE VARCHAR(36)"
                )
            )
            print(f"type fixed: {name} -> VARCHAR(36)")
        result = await conn.execute(
            text(
                "SELECT column_name, data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'oe_projects_award_pipeline' "
                "AND column_name IN ('seal_completed_by', 'feedback_sent_by', "
                "'pay10_received_by', 'client_approved_by') "
                "ORDER BY column_name"
            )
        )
        types = {r[0]: f"{r[1]}({r[2]})" for r in result.all()}
    await engine.dispose()
    return types


types = asyncio.run(_main())
for name, ddl in types.items():
    print(f"  {name}: {ddl}")
if not all(types.get(n, "").startswith("character varying") for n in COLUMNS):
    raise SystemExit(f"UNEXPECTED TYPES: {types}")
print("DONE — both *_by columns are VARCHAR now. Start the backend.")
