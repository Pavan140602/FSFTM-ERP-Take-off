# OE-DELIVERY: 2026-10-29-detect-router-patch
"""Add the Auto-detect endpoints to the takeoff router.

Run once from the repo root (the sibling file
backend/app/modules/takeoff/detect.py must be in place first):

    python patch_takeoff_detect.py

Adds, just before the AI Analysis section (requires the doc-intel
endpoints from 2026-10-28 — the access helper is reused):

    GET /documents/{doc_id}/detect/summary/    - set summary
    GET /documents/{doc_id}/detect/{category}/ - one category (?page=)

Anchor-verified + idempotent: anchors are checked BEFORE anything is
written; on any mismatch the file is left untouched. A .bak copy is
written first. Restart the backend afterwards.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("backend/app/modules/takeoff/router.py")

ANCHOR_SECTION = "# ── AI Analysis ──"
ALREADY_MARKER = "detect/summary"

BLOCK = '''# OE-DELIVERY: 2026-10-29-detect
# ── Auto-detect (Detect panel) ─────────────────────────────────────
# Reads the uploaded drawing file itself (PyMuPDF word positions, so
# marks land on the sheet): general-notes summary first, then category
# detection with Standards Library weights and a schedule cross-check.
# Same permission (takeoff.read) and tenant gate as doc-intel above
# (see detect.py in this module).


@router.get(
    "/documents/{doc_id}/detect/summary/",
    dependencies=[Depends(RequirePermission("takeoff.read"))],
)
async def get_detect_summary(
    doc_id: str,
    user_id: CurrentUserId = None,  # type: ignore[assignment]
    service: TakeoffService = Depends(_get_service),
    session: SessionDep = None,  # type: ignore[assignment]
) -> dict:
    """Set summary for the Detect panel: notes rules, schedules, census."""
    from app.modules.takeoff import detect as detect_svc

    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    return await detect_svc.build_summary(session, doc)


@router.get(
    "/documents/{doc_id}/detect/{category}/",
    dependencies=[Depends(RequirePermission("takeoff.read"))],
)
async def run_detect_category(
    doc_id: str,
    category: str,
    page: int | None = Query(default=None),
    user_id: CurrentUserId = None,  # type: ignore[assignment]
    service: TakeoffService = Depends(_get_service),
    session: SessionDep = None,  # type: ignore[assignment]
) -> dict:
    """Detect one member category (beams, studs, ...) in the document."""
    from app.modules.takeoff import detect as detect_svc

    doc = await _doc_intel_document(doc_id, str(user_id) if user_id else "", service, session)
    return await detect_svc.run_detect(session, doc, category, page)


'''


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if ALREADY_MARKER in text:
        print("Already applied: detect endpoints present, nothing changed.")
        return 0
    if "_doc_intel_document" not in text:
        print("PREREQUISITE MISSING: doc-intel endpoints not found — apply patch_takeoff_doc_intel.py first. Nothing changed.")
        return 1
    if text.count(ANCHOR_SECTION) != 1:
        print(f"ANCHOR MISSING: '{ANCHOR_SECTION}' found {text.count(ANCHOR_SECTION)} times, need 1. Nothing changed.")
        return 1
    backup = TARGET.with_suffix(".py.bak-detect")
    shutil.copy2(TARGET, backup)
    text = text.replace(ANCHOR_SECTION, BLOCK + ANCHOR_SECTION, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Restart the backend for the new endpoints to load.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
