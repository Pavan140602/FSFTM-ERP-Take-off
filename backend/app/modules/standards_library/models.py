# OE-DELIVERY: 2026-10-29-standards-library-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Standards Library ORM models.

Tables:
    oe_standards_section   - one row per steel section/member with its
                             published properties (AISC shapes, SSMA
                             cold-formed members). Seeded from the
                             official AISC Shapes Database v16.0 and the
                             SSMA Technical Guide.
    oe_standards_division  - CSI MasterFormat divisions and the sections
                             FSFTM scopes work under (05 40 00 family,
                             09 22 16, the rest of Division 05).
    oe_standards_document  - code-book shelf: one row per uploaded code
                             PDF (AISC 360, AISI S100, AWS D1.1/D1.3,
                             OSHA 1926, ...). Ask-the-Code indexes these.
"""

from sqlalchemy import JSON, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StandardsSection(Base):
    """A steel section or cold-formed member with published properties."""

    __tablename__ = "oe_standards_section"
    __table_args__ = (
        UniqueConstraint("source", "designation", name="uq_standards_section_source_designation"),
    )

    source: Mapped[str] = mapped_column(String(20), index=True)  # AISC | SSMA
    standard: Mapped[str] = mapped_column(String(120), default="")
    designation: Mapped[str] = mapped_column(String(80), index=True)  # manual label, e.g. HSS6X2X1/8
    edi_name: Mapped[str | None] = mapped_column(String(80), nullable=True)  # e.g. HSS6X2X.125
    lookup_key: Mapped[str] = mapped_column(String(80), index=True)  # normalized designation
    edi_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(16), default="")  # W, HSS, C, L, S (SSMA), T (SSMA), ...
    division: Mapped[str] = mapped_column(String(10), default="")  # MasterFormat section, e.g. 05 12 00
    weight_lb_ft: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_in2: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_in: Mapped[float | None] = mapped_column(Float, nullable=True)
    ix_in4: Mapped[float | None] = mapped_column(Float, nullable=True)
    sx_in3: Mapped[float | None] = mapped_column(Float, nullable=True)
    design_thickness_in: Mapped[float | None] = mapped_column(Float, nullable=True)  # SSMA
    fy_ksi: Mapped[int | None] = mapped_column(Integer, nullable=True)  # SSMA effective-property row
    properties: Mapped[dict] = mapped_column(JSON, default=dict)


class StandardsDivision(Base):
    """A MasterFormat division, or one detailed section under a division."""

    __tablename__ = "oe_standards_division"

    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # 05 | 05 40 00
    title: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(12), default="division")  # division | section
    parent_code: Mapped[str | None] = mapped_column(String(10), nullable=True)  # sections -> their division


class StandardsDocument(Base):
    """A code book on the library shelf (PDF uploaded by the company)."""

    __tablename__ = "oe_standards_document"

    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(String(60), default="")  # AISC | AISI | AWS | OSHA | ASTM | Other
    code: Mapped[str] = mapped_column(String(60), default="")  # e.g. AISC 360, AWS D1.3
    edition: Mapped[str] = mapped_column(String(30), default="")  # e.g. 2022, -22
    division: Mapped[str] = mapped_column(String(10), default="")
    file_path: Mapped[str] = mapped_column(String(600), default="")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    index_status: Mapped[str] = mapped_column(String(20), default="not_indexed")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
