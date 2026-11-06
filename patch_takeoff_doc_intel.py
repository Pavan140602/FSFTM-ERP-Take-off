# OE-DELIVERY: 2026-10-28-doc-intel-router-patch
"""Patch live backend/app/modules/takeoff/router.py: add Document
Intelligence endpoints for the PDF Measurements AI Assistant panel.

Run once from the repo root (backend STOPPED is not required for a
router edit, but restart the backend afterwards):

    python patch_takeoff_doc_intel.py

Anchor-verified + idempotent: every anchor is checked BEFORE anything
is written; on any mismatch the file is left untouched. A .bak copy is
written next to the file first. If the section is already present the
script reports "already applied" and changes nothing.

Endpoints added (all under /api/v1/takeoff, same permission + access
gate as the existing document download):
    GET  /documents/{doc_id}/doc-intel/          - page summary
    GET  /documents/{doc_id}/doc-intel/search/  - keyword search (?q=)
    POST /documents/{doc_id}/doc-intel/ocr/     - start OCR build
    POST /documents/{doc_id}/doc-intel/ask/     - ask AI about the doc

Requires the sibling file backend/app/modules/takeoff/doc_intel.py
(delivered alongside this script).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("backend/app/modules/takeoff/router.py")

ANCHOR_SECTION = "# ── AI Analysis ──"
ALREADY_MARKER = "doc-intel"

NEW_SECTION = '''
# OE-DELIVERY: 2026-10-28-doc-intel
# ── Document intelligence (AI Assistant panel) ─────────────────────────
# Reads the per-page text the upload flow already extracted
# (TakeoffDocument.page_data) and exposes it to the AI Assistant tab in
# PDF Measurements. Same permission (takeoff.read) and same tenant gate
# (_verify_takeoff_doc_access) as the document download above. No new
# table: OCR results live in metadata_["doc_intel_ocr"] (see doc_intel).


class DocIntelAskBody(BaseModel):
    provider: str = Field(default="groq")
    question: str = Field(default="")


async def _doc_intel_document(
    doc_id: str,
    user_id: str,
    service: TakeoffService,
    session: SessionDep,
):
    """Load a takeoff document or raise 404 (bad id counts as not found)."""
    try:
        doc = await service.get_document(doc_id)
    except (ValueError, TypeError):
        doc = None
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=translate("errors.document_not_found", locale=get_locale()),
        )
    await _verify_takeoff_doc_access(doc, str(user_id) if user_id else "", session)
    return doc


@router.get(
    "/documents/{doc_id}/doc-intel/",
    dependencies=[Depends(RequirePermission("takeoff.read"))],
)
async def get_doc_intel(
    doc_id: str,
    user_id: CurrentUserId = None,  # type: ignore[assignment]
    service: TakeoffService = Depends(_get_service),
    session: SessionDep = None,  # type: ignore[assignment]
) -> dict:
    """Page summary for the AI Assistant panel (readable/scanned counts)."""
    from app.modules.takeoff import doc_intel

    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    return doc_intel.build_summary(doc)


@router.get(
    "/documents/{doc_id}/doc-intel/search/",
    dependencies=[Depends(RequirePermission("takeoff.read"))],
)
async def search_doc_intel(
    doc_id: str,
    q: str = Query(default=""),
    user_id: CurrentUserId = None,  # type: ignore[assignment]
    service: TakeoffService = Depends(_get_service),
    session: SessionDep = None,  # type: ignore[assignment]
) -> dict:
    """Keyword search across the document's page texts, with snippets."""
    from app.modules.takeoff import doc_intel

    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    return {"query": q, "matches": doc_intel.search_pages(doc, q)}


@router.post(
    "/documents/{doc_id}/doc-intel/ocr/",
    dependencies=[Depends(RequirePermission("takeoff.read"))],
)
async def start_doc_intel_ocr(
    doc_id: str,
    user_id: CurrentUserId = None,  # type: ignore[assignment]
    service: TakeoffService = Depends(_get_service),
    session: SessionDep = None,  # type: ignore[assignment]
) -> dict:
    """Start a background OCR pass over the document's text-less pages."""
    import asyncio

    from app.modules.takeoff import doc_intel

    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    available, reason = doc_intel.ocr_available()
    if not available:
        return {"started": False, "ocr_available": False, "message": reason}
    asyncio.create_task(doc_intel.run_ocr_build(str(doc.id)))
    return {"started": True, "ocr_available": True}


@router.post(
    "/documents/{doc_id}/doc-intel/ask/",
    dependencies=[
        Depends(RequirePermission("takeoff.read")),
        Depends(RequirePermission("ai.estimate")),
    ],
)
async def ask_doc_intel(
    doc_id: str,
    body: DocIntelAskBody,
    user_id: CurrentUserId = None,  # type: ignore[assignment]
    service: TakeoffService = Depends(_get_service),
    session: SessionDep = None,  # type: ignore[assignment]
) -> dict:
    """Answer a question from the document's own page texts via AI."""
    from app.modules.takeoff import doc_intel

    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    try:
        return await doc_intel.ask_about_document(
            doc,
            body.provider,
            body.question,
            str(user_id) if user_id else "",
            session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

'''


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if "doc-intel" in text and "DocIntelAskBody" in text:
        print("Already applied: doc-intel endpoints present, nothing changed.")
        return 0
    if ANCHOR_SECTION not in text:
        print(f"ANCHOR MISSING: {ANCHOR_SECTION!r} not found, nothing changed.")
        return 1
    backup = TARGET.with_suffix(".py.bak")
    shutil.copy2(TARGET, backup)
    text = text.replace(ANCHOR_SECTION, NEW_SECTION + "\n" + ANCHOR_SECTION, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Restart the backend for the new endpoints to load.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
