#!/usr/bin/env python3
"""Create the oe_projects_estimation_review table manually.

Run this ONCE from the repo root with the backend venv:
    .\\.venv\\Scripts\\Activate.ps1
    python create_estimation_review_table.py
"""
import asyncio
import sys
sys.path.insert(0, "backend")

from sqlalchemy import text
from app.database import get_session_factory

async def main():
    factory = get_session_factory()
    async with factory() as session:
        # Check if table exists
        result = await session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'oe_projects_estimation_review')"
        ))
        exists = result.scalar()
        if exists:
            print("Table already exists - nothing to do.")
            return

        print("Creating table oe_projects_estimation_review...")
        await session.execute(text("""
            CREATE TABLE oe_projects_estimation_review (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES oe_projects(id) ON DELETE CASCADE,
                submitted_by UUID NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                lead_estimator_id UUID NULL,
                coordinator_id UUID NULL,
                manager_id UUID NULL,
                manager_approved_at TIMESTAMPTZ NULL,
                note VARCHAR(2000) NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await session.execute(text(
            "CREATE INDEX ix_oe_projects_estimation_review_project_id "
            "ON oe_projects_estimation_review (project_id)"
        ))
        await session.commit()
        print("Table created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
