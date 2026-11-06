# OE-DELIVERY: 2026-10-29-standards-library-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Standards Library service: designation normalization, lookup, search.

Drawings label members the way the AISC Manual prints them - fractions
for HSS walls (HSS6X2X1/8) - while the AISC database's electronic (EDI)
name uses decimals (HSS6X2X.125). Lookup therefore matches a small set
of candidate keys against both the manual-label key and the EDI key, so
either form, in any case, with or without spaces, finds the same row.

A designation that parses as SSMA but is not in the seeded table is
still answered from the SSMA decoder (geometry and thickness), with no
weight - the estimator sees it as a decoded result, never a silent miss.
"""

from __future__ import annotations

import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.standards_library.models import (
    StandardsDivision,
    StandardsDocument,
    StandardsSection,
)
from app.modules.standards_library.ssma_decoder import decode_ssma

# HSS wall fractions as printed in the Manual -> EDI decimal form.
_FRACTION_TO_EDI = {
    "1/8": ".125",
    "3/16": ".188",
    "1/4": ".250",
    "5/16": ".313",
    "3/8": ".375",
    "1/2": ".500",
    "5/8": ".625",
    "3/4": ".750",
    "7/8": ".875",
    "1": "1.000",
}
_EDI_TO_FRACTION = {v: k for k, v in _FRACTION_TO_EDI.items()}


def normalize_key(text: str) -> str:
    """Uppercase, drop spaces, unify the multiplication sign."""
    return re.sub(r"\s+", "", str(text or "")).upper().replace("×", "X")


def _convert_segments(key: str, mapping: dict[str, str]) -> str:
    parts = key.split("X")
    return "X".join(mapping.get(p, p) for p in parts)


def fraction_to_edi(key: str) -> str:
    """HSS6X2X1/8 -> HSS6X2X.125 (segment-wise, other shapes unchanged)."""
    return _convert_segments(key, _FRACTION_TO_EDI)


def edi_to_fraction(key: str) -> str:
    """HSS6X2X.125 -> HSS6X2X1/8."""
    return _convert_segments(key, _EDI_TO_FRACTION)


def candidate_keys(text: str) -> list[str]:
    """All key forms a drawing label or typed query could match under."""
    base = normalize_key(text)
    keys = {base, fraction_to_edi(base), edi_to_fraction(base)}
    return sorted(keys)


def _num(value) -> float | None:
    """Coerce a seed value to float; '–' / '' / text become None.

    The AISC database marks not-applicable numeric cells with an
    en-dash string, which must never reach a Float column.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def section_values_from_seed(row: dict) -> dict:
    """Map one seed-package row (AISC or SSMA JSON) to model values."""
    designation = row["designation"]
    lookup_key = normalize_key(designation)
    edi_name = row.get("edi_name")
    if edi_name:
        edi_key = normalize_key(edi_name)
    elif designation.upper().startswith("HSS"):
        edi_key = fraction_to_edi(lookup_key)
    else:
        edi_key = lookup_key
    values = {
        "source": row["source"],
        "standard": row.get("standard", ""),
        "designation": designation,
        "edi_name": edi_name,
        "lookup_key": lookup_key,
        "edi_key": edi_key,
        "type": row.get("type", ""),
        "division": row.get("division", ""),
        "weight_lb_ft": _num(row.get("weight_lb_ft")),
        "area_in2": _num(row.get("area_in2")),
        "depth_in": _num(row.get("depth_in")),
        "ix_in4": _num(row.get("ix_in4")),
        "sx_in3": _num(row.get("sx_in3")),
        "design_thickness_in": _num(row.get("design_thickness_in")),
        "fy_ksi": row.get("fy_ksi"),
        "properties": row.get("properties") or row,
    }
    if values["depth_in"] is None and row["source"] == "SSMA":
        decoded = decode_ssma(designation)
        if decoded:
            values["depth_in"] = decoded["depth_in"]
    return values


async def lookup_section(session: AsyncSession, query: str) -> dict:
    """Exact designation lookup. Returns {match, decoded, query}."""
    keys = candidate_keys(query)
    stmt = (
        select(StandardsSection)
        .where(or_(StandardsSection.lookup_key.in_(keys), StandardsSection.edi_key.in_(keys)))
        .limit(1)
    )
    row = (await session.execute(stmt)).scalars().first()
    if row is not None:
        return {"match": row, "decoded": None, "query": query}
    decoded = decode_ssma(normalize_key(query))
    return {"match": None, "decoded": decoded, "query": query}


async def search_sections(
    session: AsyncSession, query: str, limit: int = 50
) -> list[StandardsSection]:
    """Partial designation search (prefix-friendly), for the library page."""
    key = normalize_key(query)
    like = f"%{key}%"
    stmt = (
        select(StandardsSection)
        .where(
            or_(
                StandardsSection.lookup_key.like(like),
                StandardsSection.edi_key.like(like),
            )
        )
        .order_by(StandardsSection.source, StandardsSection.designation)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def library_index(session: AsyncSession) -> dict:
    """Divisions, detailed sections, documents and per-source counts."""
    divisions = list(
        (await session.execute(select(StandardsDivision).order_by(StandardsDivision.code)))
        .scalars()
        .all()
    )
    documents = list(
        (await session.execute(select(StandardsDocument).order_by(StandardsDocument.title)))
        .scalars()
        .all()
    )
    counts = (
        await session.execute(
            select(StandardsSection.source, func.count(StandardsSection.id)).group_by(
                StandardsSection.source
            )
        )
    ).all()
    return {
        "divisions": [d for d in divisions if d.kind == "division"],
        "sections": [d for d in divisions if d.kind == "section"],
        "documents": documents,
        "counts": {source: count for source, count in counts},
    }

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
    return row
