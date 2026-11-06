# OE-DELIVERY 2026-11-04-fast-upload: answer an upload after a quick text-only read; the full
# (table) extraction runs in the background and updates the document; "Extract tables"
# runs it on demand if it has not finished yet.
from pathlib import Path
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new):
    global s
    if s.count(old) != 1:
        print('ANCHOR FAIL', s.count(old), old[:140])
        sys.exit(1)
    s = s.replace(old, new)


rep('''        parsed = await _parse_pdf_isolated(file_path, filename=filename)
        if parsed is None:''', '''        # Quick text-only read first so the upload answers in seconds; the full
        # table extraction (about a second per CAD sheet) follows in the
        # background (OE-DELIVERY 2026-11-04-fast-upload).
        parsed = await _parse_pdf_fast(file_path, filename=filename)
        tables_pending = parsed is not None and parsed[0] > 0
        if parsed is None:
            parsed = await _parse_pdf_isolated(file_path, filename=filename)
        if parsed is None:''')
rep('''        if parse_truncated:
            doc_metadata["parse_truncated"] = True
            doc_metadata["parse_page_limit"] = _parse_max_pages()''', '''        if parse_truncated:
            doc_metadata["parse_truncated"] = True
            doc_metadata["parse_page_limit"] = _parse_max_pages()
        if tables_pending and not parse_degraded:
            doc_metadata["tables_pending"] = True''')
rep('''        try:
            return await self.repo.create(doc)
        except IntegrityError:''', '''        try:
            created = await self.repo.create(doc)
            if tables_pending and not parse_degraded:
                _schedule_full_parse(created.id, file_path, filename)
            return created
        except IntegrityError:''')

# extract_tables: run the full extraction now if the background one has not finished
rep('''    async def extract_tables(self, doc_id: str) -> dict:
        """Extract table data from an already-uploaded document."""
        doc = await self.repo.get_by_id(uuid.UUID(doc_id))
        if doc is None:
            return {"elements": [], "summary": {"total_elements": 0, "categories": {}}}
''', '''    async def extract_tables(self, doc_id: str) -> dict:
        """Extract table data from an already-uploaded document."""
        doc = await self.repo.get_by_id(uuid.UUID(doc_id))
        if doc is None:
            return {"elements": [], "summary": {"total_elements": 0, "categories": {}}}
        if (doc.metadata_ or {}).get("tables_pending") and doc.file_path:
            # The background table pass has not finished: run it now.
            await _apply_full_parse(doc, Path(doc.file_path), doc.filename)
            await self.session.flush()
''')

HELPERS = '''

# ── fast upload (OE-DELIVERY 2026-11-04-fast-upload) ───────────────────


async def _parse_pdf_fast(pdf_path: Path, *, filename: str | None) -> tuple[int, list[dict], bool, str | None] | None:
    """Text-only read with PyMuPDF (no table finder) - a few seconds even for
    a large drawing set. Same result contract as :func:`_parse_pdf_isolated`;
    ``None`` when it fails, so the caller falls back to the full parse."""
    import asyncio

    from app.modules.takeoff import pdf_extract_worker

    def _run() -> dict:
        fp = pdf_extract_worker._fingerprint(str(pdf_path), filename)
        return pdf_extract_worker._extract_with_pymupdf(str(pdf_path), _parse_max_pages(), fp)

    try:
        result = await asyncio.to_thread(_run)
    except Exception:
        logger.warning("takeoff.fast parse failed (filename=%r) - using the full parse", filename, exc_info=True)
        return None
    page_count = int(result.get("page_count", 0) or 0)
    pages = result.get("pages") or []
    if not page_count or not isinstance(pages, list) or result.get("reader_error"):
        return None
    return page_count, pages, bool(result.get("truncated", False)), None


async def _apply_full_parse(doc: Any, pdf_path: Path, filename: str | None) -> bool:
    """Run the full (table) extraction and store it on ``doc``."""
    parsed = await _parse_pdf_isolated(pdf_path, filename=filename)
    meta = dict(doc.metadata_ or {})
    meta.pop("tables_pending", None)
    if parsed is None:
        meta["tables_degraded"] = True
        doc.metadata_ = meta
        return False
    _count, page_data, _trunc, _err = parsed
    if page_data:
        doc.page_data = page_data
        doc.extracted_text = "\\n\\n".join(p["text"] for p in page_data if p.get("text"))
    doc.metadata_ = meta
    return True


def _schedule_full_parse(doc_id: Any, pdf_path: Path, filename: str | None) -> None:
    """Detached background table extraction on its own DB session."""
    import asyncio

    async def _runner() -> None:
        from app.database import async_session_factory

        parsed_once = False
        # The upload's own transaction commits right after this returns;
        # wait for the row before touching it.
        for _attempt in range(60):
            async with async_session_factory() as bg:
                try:
                    from app.modules.takeoff.models import TakeoffDocument

                    doc = await bg.get(TakeoffDocument, doc_id)
                    if doc is None:
                        await asyncio.sleep(1.0)
                        continue
                    if not (doc.metadata_ or {}).get("tables_pending"):
                        return
                    await _apply_full_parse(doc, pdf_path, filename)
                    parsed_once = True
                    await bg.commit()
                    return
                except Exception:
                    logger.exception("takeoff.background full parse failed for %s", doc_id)
                    await bg.rollback()
                    return
        if not parsed_once:
            logger.warning("takeoff.background full parse: document %s never appeared", doc_id)

    try:
        asyncio.create_task(_runner())  # noqa: RUF006 - detached background job
    except RuntimeError:
        logger.warning("takeoff.background full parse %s: no running loop", doc_id)
'''
rep('''async def _parse_pdf_isolated(
    pdf_path: Path,''', HELPERS.strip('\n') + '''


async def _parse_pdf_isolated(
    pdf_path: Path,''')
P.write_text(s, encoding='utf-8')
print('ok')
