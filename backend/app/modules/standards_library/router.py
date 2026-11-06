# OE-DELIVERY: 2026-10-29-standards-library-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Standards Library API routes.

Mounted by the module loader at ``/api/v1/standards-library`` (the
``/api/v1/standards_library`` form is mirrored automatically).

Endpoints:
    GET    /                       - divisions, sections, documents, counts
    GET    /sections/lookup/?q=    - exact designation lookup (drawing label
                                     or EDI form), with SSMA decode fallback
    GET    /sections/search/?q=    - partial designation search
    GET    /documents/             - code-book shelf
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.dependencies import RequirePermission, SessionDep
from app.modules.standards_library import service
from app.modules.standards_library.schemas import (
    DivisionOut,
    DocumentOut,
    LibraryIndexOut,
    LookupOut,
    SectionOut,
)

router = APIRouter(tags=["standards-library"])

_READ = [Depends(RequirePermission("standards_library.read"))]
_MANAGE = [Depends(RequirePermission("standards_library.manage"))]


def _section_out(row) -> SectionOut:
    return SectionOut(
        id=row.id,
        source=row.source,
        standard=row.standard,
        designation=row.designation,
        edi_name=row.edi_name,
        type=row.type,
        division=row.division,
        weight_lb_ft=row.weight_lb_ft,
        area_in2=row.area_in2,
        depth_in=row.depth_in,
        ix_in4=row.ix_in4,
        sx_in3=row.sx_in3,
        design_thickness_in=row.design_thickness_in,
        fy_ksi=row.fy_ksi,
        properties=row.properties or {},
    )


@router.get("/", response_model=LibraryIndexOut, dependencies=_READ)
async def index(session: SessionDep) -> LibraryIndexOut:
    data = await service.library_index(session)

    def _division_out(d) -> DivisionOut:
        return DivisionOut(code=d.code, title=d.title, kind=d.kind, parent_code=d.parent_code)

    return LibraryIndexOut(
        divisions=[_division_out(d) for d in data["divisions"]],
        sections=[_division_out(d) for d in data["sections"]],
        documents=[
            DocumentOut(
                id=d.id,
                title=d.title,
                body=d.body,
                code=d.code,
                edition=d.edition,
                division=d.division,
                page_count=d.page_count,
                index_status=d.index_status,
            )
            for d in data["documents"]
        ],
        counts=data["counts"],
    )


@router.get("/sections/lookup/", response_model=LookupOut, dependencies=_READ)
async def lookup(session: SessionDep, q: str = Query(min_length=1)) -> LookupOut:
    result = await service.lookup_section(session, q)
    return LookupOut(
        query=result["query"],
        match=_section_out(result["match"]) if result["match"] is not None else None,
        decoded=result["decoded"],
    )


@router.get("/sections/search/", response_model=list[SectionOut], dependencies=_READ)
async def search(
    session: SessionDep, q: str = Query(min_length=1), limit: int = Query(default=50, ge=1, le=200)
) -> list[SectionOut]:
    rows = await service.search_sections(session, q, limit=limit)
    return [_section_out(r) for r in rows]


@router.post("/documents/", response_model=DocumentOut, dependencies=_MANAGE)
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


@router.get("/documents/", response_model=list[DocumentOut], dependencies=_READ)
async def documents(session: SessionDep) -> list[DocumentOut]:
    data = await service.library_index(session)
    return [
        DocumentOut(
            id=d.id,
            title=d.title,
            body=d.body,
            code=d.code,
            edition=d.edition,
            division=d.division,
            page_count=d.page_count,
            index_status=d.index_status,
        )
        for d in data["documents"]
    ]
