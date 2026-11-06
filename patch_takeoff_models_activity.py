# OE-DELIVERY: 2026-10-29-doc-intel-v2-models-patch
"""Patch live backend/app/modules/takeoff/models.py: add the
DocIntelActivity table for the AI Assistant panel's daily work log.

Run once from the repo root, then restart the backend:

    python patch_takeoff_models_activity.py

The table is NEW, so create_all builds it on the next backend start
(the product never runs alembic upgrade; new tables are create_all-
safe, no column script needed).

Anchor-verified + idempotent: the anchor is checked BEFORE anything
is written; on any mismatch the file is left untouched. A .bak copy
is written next to the file first. If the class is already present
the script reports "already applied" and changes nothing.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("backend/app/modules/takeoff/models.py")

ANCHOR = "class TakeoffMeasurement(Base):"
ALREADY_MARKER = "class DocIntelActivity"

NEW_CLASS = '''class DocIntelActivity(Base):
    """AI Assistant panel activity log (daily work tracking).

    One row per panel action (search / ask / ocr) so the estimator can
    review their day in the panel's Today card. Append-only with no
    foreign keys on purpose: rows must survive document/project
    deletion, and the denormalised document_name keeps the history
    readable afterwards. New table - create_all builds it, no column
    heal needed.
    """

    __tablename__ = "oe_takeoff_doc_intel_activity"
    __table_args__ = (
        Index("ix_doc_intel_activity_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, default=None)
    project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, default=None)
    document_name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="")  # search | ask | ocr
    detail: Mapped[dict] = mapped_column(  # type: ignore[assignment]
        JSON, nullable=False, default=dict, server_default="{}"
    )

    def __repr__(self) -> str:
        return f"<DocIntelActivity {self.action} {self.document_name}>"


'''


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if ALREADY_MARKER in text:
        print("Already applied: DocIntelActivity present, nothing changed.")
        return 0
    if text.count(ANCHOR) != 1:
        print(f"ANCHOR MISSING/AMBIGUOUS: {ANCHOR!r} found {text.count(ANCHOR)}x, nothing changed.")
        return 1
    backup = TARGET.with_suffix(".py.bak")
    shutil.copy2(TARGET, backup)
    text = text.replace(ANCHOR, NEW_CLASS + ANCHOR, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Restart the backend so create_all builds oe_takeoff_doc_intel_activity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
