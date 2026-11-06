# OE-DELIVERY: 2026-10-29-standards-library-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Standards Library API schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SectionOut(BaseModel):
    id: UUID
    source: str
    standard: str = ""
    designation: str
    edi_name: str | None = None
    type: str = ""
    division: str = ""
    weight_lb_ft: float | None = None
    area_in2: float | None = None
    depth_in: float | None = None
    ix_in4: float | None = None
    sx_in3: float | None = None
    design_thickness_in: float | None = None
    fy_ksi: int | None = None
    properties: dict = {}


class DecodedOut(BaseModel):
    designation: str
    depth_in: float
    style: str
    style_name: str
    flange_in: float
    mil: int
    design_thickness_in: float
    min_thickness_in: float
    gauge_label: str | None = None


class LookupOut(BaseModel):
    query: str
    match: SectionOut | None = None
    decoded: DecodedOut | None = None


class DivisionOut(BaseModel):
    code: str
    title: str = ""
    kind: str = "division"
    parent_code: str | None = None


class DocumentOut(BaseModel):
    id: UUID
    title: str
    body: str = ""
    code: str = ""
    edition: str = ""
    division: str = ""
    page_count: int = 0
    index_status: str = "not_indexed"


class LibraryIndexOut(BaseModel):
    divisions: list[DivisionOut] = []
    sections: list[DivisionOut] = []
    documents: list[DocumentOut] = []
    counts: dict[str, int] = {}
