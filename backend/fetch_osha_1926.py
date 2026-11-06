"""Fetch OSHA 29 CFR 1926 (public domain) onto the Standards Library shelf.

OE-DELIVERY: 2026-10-29-standards-library-v1

Downloads the official CFR Title 29 Volume 8 package PDF from govinfo
(Part 1926 - Safety and Health Regulations for Construction - is the
bulk of that volume), validates it, stores it with the other shelved
code books, and registers it in oe_standards_document. Idempotent: if
the 2024 OSHA row already exists it only refreshes the file and counts.

US federal regulations are public domain - no licence is needed.

Run with the backend STOPPED, from the repo root, with the venv python
(needs internet, downloads about 11 MB). Place this file in backend/
first, with the standards_library module already installed and its
tables created (run seed_standards_library.py first if you have not):
    .\\.venv\\Scripts\\python.exe backend\\fetch_osha_1926.py
Then start the backend again.
"""

from __future__ import annotations

import asyncio
import os
import urllib.request
from pathlib import Path

from app.core import embedded_pg

data_dir = Path.home() / ".openestimate"
if embedded_pg.is_requested():
    if not embedded_pg.boot(data_dir):
        raise SystemExit("Embedded PostgreSQL could not start - see the log above.")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.storage import resolve_data_dir
from app.modules.standards_library.models import StandardsDocument

URL = "https://www.govinfo.gov/content/pkg/CFR-2024-title29-vol8/pdf/CFR-2024-title29-vol8.pdf"
TITLE = "OSHA Safety and Health Regulations for Construction"
CODE = "29 CFR 1926"
EDITION = "2024"
STORED_NAME = "osha-29cfr1926-2024.pdf"

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    raise SystemExit("No DATABASE_URL after boot - cannot connect.")


def download() -> bytes:
    print(f"Downloading {URL} ...")
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise SystemExit("Download did not return a PDF - aborting, nothing registered.")
    print(f"Downloaded {len(data) / 1_000_000:.1f} MB, PDF header OK.")
    return data


async def _main(content: bytes) -> None:
    folder = Path(resolve_data_dir()) / "standards_library"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / STORED_NAME
    path.write_bytes(content)
    page_count = 0
    try:
        import fitz

        doc = fitz.open(stream=content, filetype="pdf")
        page_count = doc.page_count
        doc.close()
    except Exception:
        page_count = 0
    print(f"Stored at {path} ({page_count} pages).")

    engine = create_async_engine(db_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        stmt = select(StandardsDocument).where(
            StandardsDocument.code == CODE, StandardsDocument.edition == EDITION
        )
        row = (await session.execute(stmt)).scalars().first()
        if row is None:
            row = StandardsDocument(title=TITLE, body="OSHA", code=CODE, edition=EDITION)
            session.add(row)
            action = "registered"
        else:
            action = "refreshed"
        row.title = TITLE
        row.body = "OSHA"
        row.file_path = str(path)
        row.page_count = page_count
        row.index_status = "not_indexed"
        row.metadata_ = {"source_url": URL, "package": "CFR-2024-title29-vol8", "size_bytes": len(content)}
        await session.commit()
    await engine.dispose()
    print(f"DONE - OSHA 29 CFR 1926 (2024) {action} on the shelf: {page_count} pages.")


if __name__ == "__main__":
    asyncio.run(_main(download()))
