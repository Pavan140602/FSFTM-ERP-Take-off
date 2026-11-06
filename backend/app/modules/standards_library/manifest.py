# OE-DELIVERY: 2026-10-29-standards-library-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Standards Library module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_standards_library",
    version="0.1.0",
    display_name="Standards Library",
    description=(
        "Codes and standards reference library: structured section-property "
        "tables (AISC shapes, SSMA cold-formed members) with designation "
        "lookup for estimating, plus a document shelf for code books "
        "(AISC 360, AISI S100, AWS, OSHA) used by Ask-the-Code."
    ),
    author="OpenConstructionERP Core Team",
    category="core",
    depends=[],
    auto_install=True,
    enabled=True,
)
