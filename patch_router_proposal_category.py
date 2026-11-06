"""Patch the live projects router so the Proposal+Quotation folder lists.

OE-DELIVERY: 2026-10-27-export-proposal-422fix

Why this script exists instead of a whole-file router delivery: the mirror's
router.py predates the live receipt-edit PATCH endpoint, so replacing the live
router.py with a mirror-based file would wipe that endpoint. This script edits
only the file-manager list endpoint (``GET /{project_id}/files/``) in place.

Problem: that endpoint declared ``category: FileKind | None``, so FastAPI enum
validation rejected ``category=Proposal+Quotation`` with 422 before the handler
ran. ``Proposal+Quotation`` is a Document.category value (a folder), not a
FileKind. After the patch the param is a raw string: the known folder value
passes through to the file-manager service (which now filters document rows
to that category), known kinds pass through as before, and anything else
still gets a 422, exactly as before.

Usage (from the repo root, with the project venv):
    .\\.venv\\Scripts\\python.exe patch_router_proposal_category.py
    .\\.venv\\Scripts\\python.exe patch_router_proposal_category.py backend/app/modules/projects/router.py

The script refuses to write anything unless every anchor is found exactly
once inside the file_manager_list function, and it refuses to run twice
(idempotent: a second run reports "already patched" and changes nothing).
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "OE-DELIVERY 2026-10-27-export-proposal-422fix"
DEFAULT_ROUTER = Path("backend/app/modules/projects/router.py")

OLD_PARAM = "    category: FileKind | None = Query(default=None),\n"
NEW_PARAM = "    category: str | None = Query(default=None, max_length=100),\n"

ACCESS_LINE = "    await _verify_project_access(service, project_id, user_id, session, payload)\n"
RESOLUTION_BLOCK = """\
    # OE-DELIVERY 2026-10-27-export-proposal-422fix: "Proposal+Quotation" is a
    # Document.category value (a folder), not a FileKind, so FastAPI enum
    # validation on this param used to reject it with 422 before the handler
    # ran. Accept it as a raw string and pass it through; any other unknown
    # value still gets a 422, exactly as before.
    resolved_category: FileKind | str | None = None
    if category is not None:
        if category == "Proposal+Quotation":
            resolved_category = category
        elif category in FILE_KINDS:
            resolved_category = category  # type: ignore[assignment]
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unknown file category: {category}",
            )
"""

OLD_CALL = "        category=category,\n"
NEW_CALL = "        category=resolved_category,\n"


def fail(message: str) -> int:
    print(f"PATCH FAILED: {message}")
    print(
        "Nothing was written. Check the router path and that the live file "
        "still contains the file_manager_list endpoint."
    )
    return 1


def main(argv: list[str]) -> int:
    router_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_ROUTER
    if not router_path.is_file():
        return fail(f"router file not found: {router_path}")
    text = router_path.read_text(encoding="utf-8")

    if MARKER in text:
        print(
            "Already patched: the 2026-10-27-export-proposal-422fix marker is "
            "present. Nothing changed."
        )
        return 0

    start = text.find("async def file_manager_list(")
    if start < 0:
        return fail("file_manager_list function not found.")
    # The function body ends at the next top-level decorator block.
    next_decorator = text.find("\n@", start)
    end = next_decorator if next_decorator >= 0 else len(text)
    region = text[start:end]

    for label, anchor in (
        ("category param", OLD_PARAM),
        ("access-check line", ACCESS_LINE),
        ("service call", OLD_CALL),
    ):
        count = region.count(anchor)
        if count != 1:
            return fail(
                f"{label} anchor found {count} times inside file_manager_list "
                "(expected exactly 1)."
            )

    patched_region = region.replace(OLD_PARAM, NEW_PARAM)
    patched_region = patched_region.replace(ACCESS_LINE, ACCESS_LINE + RESOLUTION_BLOCK)
    patched_region = patched_region.replace(OLD_CALL, NEW_CALL)
    if MARKER not in patched_region:
        return fail("internal error: patched region lost the marker.")

    router_path.write_text(text[:start] + patched_region + text[end:], encoding="utf-8")
    print(f"Patched OK: {router_path}")
    print(
        "Changed inside file_manager_list only: category param type, "
        "category resolution block, service call argument."
    )
    print("Next step: restart the backend, then open the Proposal+Quotation folder again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
