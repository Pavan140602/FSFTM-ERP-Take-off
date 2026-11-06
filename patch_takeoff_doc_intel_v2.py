# OE-DELIVERY: 2026-10-29-doc-intel-v2-router-patch
"""Patch live backend/app/modules/takeoff/router.py (v2, on top of the
2026-10-28 doc-intel endpoints): log panel activity and serve the
Today summary for the AI Assistant panel's daily work tracking.

Run once from the repo root, AFTER patch_takeoff_doc_intel.py (v1)
and patch_takeoff_models_activity.py, then restart the backend:

    python patch_takeoff_doc_intel_v2.py

Changes (all inside the doc-intel section added by v1):
    * search endpoint - logs a "search" activity row (query + count)
    * ask endpoint    - logs an "ask" activity row (provider + question)
    * OCR endpoint    - logs an "ocr" activity row on start
    * new endpoint    - GET /doc-intel/activity/today/ (own rows only)

Anchor-verified + idempotent: every anchor is checked BEFORE anything
is written; on any mismatch the file is left untouched. A .bak copy
is written next to the file first. If v2 is already present the
script reports "already applied" and changes nothing. Requires the
v2 doc_intel.py (log_activity / today_activity) delivered alongside.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("backend/app/modules/takeoff/router.py")

V1_MARKER = "DocIntelAskBody"
ALREADY_MARKER = "get_doc_intel_activity_today"
SECTION_ANCHOR = "# ── AI Analysis ──"

SEARCH_OLD = '''    return {"query": q, "matches": doc_intel.search_pages(doc, q)}'''
SEARCH_NEW = '''    matches = doc_intel.search_pages(doc, q)
    await doc_intel.log_activity(
        session,
        str(user_id) if user_id else "",
        doc,
        "search",
        {"query": q, "matches": len(matches)},
    )
    return {"query": q, "matches": matches}'''

ASK_OLD = '''    try:
        return await doc_intel.ask_about_document(
            doc,
            body.provider,
            body.question,
            str(user_id) if user_id else "",
            session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc'''
ASK_NEW = '''    try:
        result = await doc_intel.ask_about_document(
            doc,
            body.provider,
            body.question,
            str(user_id) if user_id else "",
            session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await doc_intel.log_activity(
        session,
        str(user_id) if user_id else "",
        doc,
        "ask",
        {"provider": body.provider, "question": body.question[:200]},
    )
    return result'''

OCR_OLD = '''    asyncio.create_task(doc_intel.run_ocr_build(str(doc.id)))
    return {"started": True, "ocr_available": True}'''
OCR_NEW = '''    asyncio.create_task(doc_intel.run_ocr_build(str(doc.id)))
    await doc_intel.log_activity(
        session, str(user_id) if user_id else "", doc, "ocr", {}
    )
    return {"started": True, "ocr_available": True}'''

ACTIVITY_ENDPOINT = '''
# OE-DELIVERY: 2026-10-29-doc-intel-v2
@router.get(
    "/doc-intel/activity/today/",
    dependencies=[Depends(RequirePermission("takeoff.read"))],
)
async def get_doc_intel_activity_today(
    user_id: CurrentUserId = None,  # type: ignore[assignment]
    session: SessionDep = None,  # type: ignore[assignment]
) -> dict:
    """Today's AI Assistant activity for the signed-in user (daily work view)."""
    from app.modules.takeoff import doc_intel

    return await doc_intel.today_activity(session, str(user_id) if user_id else "")

'''

REPLACEMENTS = (
    ("search logging", SEARCH_OLD, SEARCH_NEW),
    ("ask logging", ASK_OLD, ASK_NEW),
    ("ocr logging", OCR_OLD, OCR_NEW),
)


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if ALREADY_MARKER in text:
        print("Already applied: doc-intel v2 activity endpoints present, nothing changed.")
        return 0
    if V1_MARKER not in text:
        print("V1 MISSING: run patch_takeoff_doc_intel.py first, nothing changed.")
        return 1
    for name, old, _new in REPLACEMENTS:
        if text.count(old) != 1:
            print(f"ANCHOR MISSING/AMBIGUOUS ({name}): found {text.count(old)}x, nothing changed.")
            return 1
    if SECTION_ANCHOR not in text:
        print(f"ANCHOR MISSING: {SECTION_ANCHOR!r} not found, nothing changed.")
        return 1
    backup = TARGET.with_suffix(".py.bak2")
    shutil.copy2(TARGET, backup)
    for _name, old, new in REPLACEMENTS:
        text = text.replace(old, new, 1)
    text = text.replace(SECTION_ANCHOR, ACTIVITY_ENDPOINT + "\n" + SECTION_ANCHOR, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Restart the backend for the activity logging + Today endpoint to load.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
