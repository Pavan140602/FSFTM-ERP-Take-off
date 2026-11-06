"""Add the code-book upload endpoint to the Standards Library module.

OE-DELIVERY: 2026-10-29-standards-library-v1

Anchored insertions into the chunk-1 module files, each verified before
anything is written:
  service.py - documents_dir(), filename cleaning and create_document()
               (stores the PDF under <data dir>/standards_library/,
               counts pages, registers the shelf row);
  router.py  - POST /documents/ (multipart, standards_library.manage),
               accepting only real PDFs.

Idempotent per file: a file that already carries its marker is left
alone. If an anchor is missing or not unique, that file is not written
and the output says which anchor failed - send it back instead of
editing by hand.

Run from the repo root with plain python (stdlib only), after the
chunk-1 module files are in place:
    python patch_backend_documents.py
Then restart the backend.
"""

from __future__ import annotations

from pathlib import Path

SERVICE = Path("backend/app/modules/standards_library/service.py")
ROUTER = Path("backend/app/modules/standards_library/router.py")

SERVICE_MARKER = "async def create_document"
SERVICE_ANCHOR = '''    return {
        "divisions": [d for d in divisions if d.kind == "division"],
        "sections": [d for d in divisions if d.kind == "section"],
        "documents": documents,
        "counts": {source: count for source, count in counts},
    }'''
SERVICE_ADD = '''

# ── document shelf ────────────────────────────────────────────────


def documents_dir():
    """Folder holding the shelved code-book PDFs (created on demand)."""
    from pathlib import Path

    from app.core.storage import resolve_data_dir

    folder = Path(resolve_data_dir()) / "standards_library"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "document.pdf").strip("._")
    return cleaned or "document.pdf"


async def create_document(
    session: AsyncSession,
    *,
    filename: str,
    content: bytes,
    title: str,
    body: str,
    code: str,
    edition: str,
    division: str,
) -> StandardsDocument:
    """Store an uploaded code-book PDF and register it on the shelf."""
    import uuid

    stored = f"{uuid.uuid4().hex[:12]}-{_safe_filename(filename)}"
    path = documents_dir() / stored
    path.write_bytes(content)
    page_count = 0
    try:
        import fitz

        doc = fitz.open(stream=content, filetype="pdf")
        page_count = doc.page_count
        doc.close()
    except Exception:
        page_count = 0
    row = StandardsDocument(
        title=title or stored,
        body=body or "",
        code=code or "",
        edition=edition or "",
        division=division or "",
        file_path=str(path),
        page_count=page_count,
        index_status="not_indexed",
        metadata_={"original_filename": filename, "size_bytes": len(content)},
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row'''

ROUTER_MARKER = "async def upload_document"
ROUTER_IMPORT_ANCHOR = "from fastapi import APIRouter, Depends, Query"
ROUTER_IMPORT_NEW = "from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile"
ROUTER_DEPS_ANCHOR = '_READ = [Depends(RequirePermission("standards_library.read"))]'
ROUTER_DEPS_ADD = '\n_MANAGE = [Depends(RequirePermission("standards_library.manage"))]'
ROUTER_EP_ANCHOR = '@router.get("/documents/", response_model=list[DocumentOut], dependencies=_READ)'
ROUTER_EP_ADD = '''@router.post("/documents/", response_model=DocumentOut, dependencies=_MANAGE)
async def upload_document(
    session: SessionDep,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    body: str = Form(default=""),
    code: str = Form(default=""),
    edition: str = Form(default=""),
    division: str = Form(default=""),
) -> DocumentOut:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be shelved.")
    content = await file.read()
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a PDF.")
    row = await service.create_document(
        session,
        filename=file.filename or "document.pdf",
        content=content,
        title=title.strip(),
        body=body.strip(),
        code=code.strip(),
        edition=edition.strip(),
        division=division.strip(),
    )
    return DocumentOut(
        id=row.id,
        title=row.title,
        body=row.body,
        code=row.code,
        edition=row.edition,
        division=row.division,
        page_count=row.page_count,
        index_status=row.index_status,
    )


'''


def patch_file(path: Path, marker: str, edits: list[tuple[str, str, str]]) -> str:
    if not path.exists():
        return f"NOT FOUND: {path}"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return f"already applied: {path.name}"
    for name, anchor, replacement in edits:
        count = text.count(anchor)
        if count != 1:
            return f"ANCHOR MISSING in {path.name} ({name}): found {count}, need 1 - file NOT written"
        text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")
    return f"patched: {path.name} (now {text.count(chr(10)) + 1} lines)"


def main() -> None:
    results = [
        patch_file(SERVICE, SERVICE_MARKER, [("library_index return", SERVICE_ANCHOR, SERVICE_ANCHOR + SERVICE_ADD)]),
        patch_file(
            ROUTER,
            ROUTER_MARKER,
            [
                ("fastapi imports", ROUTER_IMPORT_ANCHOR, ROUTER_IMPORT_NEW),
                ("manage dependency", ROUTER_DEPS_ANCHOR, ROUTER_DEPS_ANCHOR + ROUTER_DEPS_ADD),
                ("documents route", ROUTER_EP_ANCHOR, ROUTER_EP_ADD + ROUTER_EP_ANCHOR),
            ],
        ),
    ]
    for line in results:
        print(line)
    if any("patched" in r for r in results):
        print("Restart the backend to load the upload endpoint.")


if __name__ == "__main__":
    main()
